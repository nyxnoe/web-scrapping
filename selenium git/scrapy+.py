import time
import random
import logging
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from collections import Counter
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote

# Logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Paths
CHROME_DRIVER_PATH = r"C:\Users\nihal\OneDrive\Desktop\web scrapping\137.0.7151.68 chromedriver-win64\chromedriver-win64\chromedriver.exe"
BROWSER_BINARY_PATH = r"C:\Users\nihal\AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe"

def get_free_proxies():
    """Fetch free proxies from free-proxy-list.net"""
    try:
        logging.info("🔍 Fetching free proxies...")
        url = "https://free-proxy-list.net/"
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.content, "html.parser")
        proxies = []
        
        for row in soup.select("table.table tbody tr"):
            tds = row.find_all("td")
            if len(tds) >= 7:
                ip = tds[0].text.strip()
                port = tds[1].text.strip()
                https = tds[6].text.strip()
                if https.lower() == "yes":
                    proxies.append(f"http://{ip}:{port}")
        
        logging.info(f"✅ Found {len(proxies)} HTTPS proxies")
        return proxies
    except Exception as e:
        logging.error(f"❌ Failed to fetch proxies: {e}")
        return []

def test_proxy(proxy):
    """Test if a proxy is working"""
    try:
        response = requests.get("https://httpbin.org/ip", 
                              proxies={"http": proxy, "https": proxy}, 
                              timeout=10)
        return response.status_code == 200
    except:
        return False

def get_working_proxy(proxies, max_attempts=3):
    """Get a working proxy from the list"""
    if not proxies:
        return None
        
    random.shuffle(proxies)
    for i, proxy in enumerate(proxies[:max_attempts]):
        logging.info(f"🔄 Testing proxy {i+1}/{max_attempts}: {proxy}")
        if test_proxy(proxy):
            logging.info(f"✅ Working proxy found: {proxy}")
            return proxy
        else:
            logging.warning(f"❌ Proxy failed: {proxy}")
    
    logging.warning("⚠️ No working proxies found, continuing without proxy...")
    return None

def close_popups(driver):
    """Close any popups that might appear"""
    popup_selectors = [
        "//button[contains(@class, '_2KpZ6l')]",  # Login popup close
        "//span[text()='✕']",  # Generic close button
        "//button[text()='✕']",  # Generic close button
        "//*[@class='_3Njdz7']",  # Another popup close
        "//button[contains(text(), 'Later')]",  # Later button
        "//span[contains(@role, 'button') and contains(text(), '✕')]",
        "//div[contains(@class, 'modal')]//button",  # Modal close buttons
        "//button[contains(@aria-label, 'close')]",  # Aria close buttons
        "//*[contains(@class, 'popup')]//button",  # Popup close buttons
    ]
    
    for selector in popup_selectors:
        try:
            element = WebDriverWait(driver, 2).until(
                EC.element_to_be_clickable((By.XPATH, selector))
            )
            element.click()
            logging.info(f"🚫 Closed popup with selector: {selector}")
            time.sleep(1)
            break  # Exit after first successful close
        except:
            continue

def setup_driver(headless=False, use_proxy=False, proxy=None):
    """Set up a Chrome (or Brave) Selenium driver with optional proxy support"""
    options = Options()
    options.binary_location = BROWSER_BINARY_PATH
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Add proxy configuration if provided
    if use_proxy and proxy:
        proxy_host = proxy.replace('http://', '').replace('https://', '')
        options.add_argument(f'--proxy-server={proxy}')
        logging.info(f"🔒 Using proxy: {proxy}")
    
    if headless:
        options.add_argument("--headless")
        
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    
    service = Service(executable_path=CHROME_DRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def analyze_website_structure(url, wait_time=10, use_proxy=False):
    """
    Analyze website structure and detect potential scrapeable elements
    """
    # Setup proxy if requested
    proxy = None
    if use_proxy:
        proxies = get_free_proxies()
        if proxies:
            proxy = get_working_proxy(proxies)
    
    driver = setup_driver(headless=False, use_proxy=use_proxy, proxy=proxy)
    detected_patterns = {}
    
    try:
        logging.info(f"🔍 Analyzing website structure: {url}")
        driver.get(url)
        time.sleep(random.uniform(3, 6))
        
        # Close any popups
        close_popups(driver)
        
        # Wait for page to load
        WebDriverWait(driver, wait_time).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Find potential container patterns
        containers = find_container_patterns(driver)
        
        # Analyze each container pattern
        for pattern_name, selector_info in containers.items():
            sample_data = analyze_container_content(driver, selector_info)
            if sample_data:
                detected_patterns[pattern_name] = {
                    'selector': selector_info['selector'],
                    'count': selector_info['count'],
                    'sample_data': sample_data,
                    'data_types': identify_data_types(sample_data)
                }
    
    except Exception as e:
        logging.error(f"❌ Analysis failed: {e}")
    finally:
        driver.quit()
    
    return detected_patterns

def find_container_patterns(driver):
    """
    Find repeating container patterns that likely contain data
    """
    containers = {}
    
    # Common container patterns to look for
    common_patterns = [
        "div[class*='item']", "div[class*='card']", "div[class*='product']",
        "div[class*='listing']", "div[class*='result']", "div[class*='post']",
        "li[class*='item']", "li[class*='product']", "li[class*='result']",
        "article", "section[class*='item']", "div[class*='tile']",
        "div[class*='box']", "div[class*='entry']", "tr"
    ]
    
    # Find elements that appear multiple times (likely containers)
    all_elements = driver.find_elements(By.CSS_SELECTOR, "*[class]")
    class_counter = Counter()
    
    for elem in all_elements:
        classes = elem.get_attribute("class")
        if classes:
            class_list = classes.split()
            for cls in class_list:
                if len(cls) > 3:  # Ignore very short class names
                    class_counter[cls] += 1
    
    # Find classes that appear multiple times (3+ times)
    frequent_classes = {cls: count for cls, count in class_counter.items() if count >= 3}
    
    pattern_id = 1
    for cls, count in sorted(frequent_classes.items(), key=lambda x: x[1], reverse=True)[:10]:
        selector = f".{cls}"
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if len(elements) >= 3:  # At least 3 similar elements
                # Check if elements have meaningful content
                sample_elem = elements[0]
                if sample_elem.text.strip() and len(sample_elem.text.strip()) > 10:
                    containers[f"Pattern_{pattern_id}"] = {
                        'selector': selector,
                        'count': len(elements),
                        'class_name': cls
                    }
                    pattern_id += 1
        except:
            continue
    
    return containers

def analyze_container_content(driver, selector_info):
    """
    Analyze the content structure within containers
    """
    try:
        elements = driver.find_elements(By.CSS_SELECTOR, selector_info['selector'])[:3]  # Analyze first 3
        content_analysis = []
        
        for elem in elements:
            item_data = {}
            
            # Find common sub-elements
            sub_elements = {
                'headings': elem.find_elements(By.CSS_SELECTOR, "h1, h2, h3, h4, h5, h6"),
                'links': elem.find_elements(By.CSS_SELECTOR, "a"),
                'images': elem.find_elements(By.CSS_SELECTOR, "img"),
                'prices': elem.find_elements(By.CSS_SELECTOR, "[class*='price'], [class*='cost'], [class*='amount']"),
                'ratings': elem.find_elements(By.CSS_SELECTOR, "[class*='rating'], [class*='star'], [class*='review']"),
                'spans': elem.find_elements(By.CSS_SELECTOR, "span"),
                'divs': elem.find_elements(By.CSS_SELECTOR, "div"),
            }
            
            for element_type, found_elements in sub_elements.items():
                if found_elements:
                    item_data[element_type] = []
                    for sub_elem in found_elements[:3]:  # Max 3 of each type
                        text = sub_elem.text.strip()
                        if text and len(text) < 200:  # Reasonable text length
                            item_data[element_type].append({
                                'text': text,
                                'tag': sub_elem.tag_name,
                                'class': sub_elem.get_attribute('class') or '',
                                'selector': generate_selector(sub_elem)
                            })
            
            content_analysis.append(item_data)
        
        return content_analysis
    except Exception as e:
        logging.error(f"Content analysis failed: {e}")
        return []

def generate_selector(element):
    """
    Generate a CSS selector for an element
    """
    try:
        tag = element.tag_name
        class_attr = element.get_attribute('class')
        
        if class_attr:
            # Use first class as selector
            first_class = class_attr.split()[0]
            return f"{tag}.{first_class}"
        else:
            return tag
    except:
        return "unknown"

def identify_data_types(sample_data):
    """
    Identify what type of data each field likely contains
    """
    data_types = {}
    
    if not sample_data:
        return data_types
    
    # Analyze patterns across samples
    for item in sample_data:
        for field_type, elements in item.items():
            if elements:
                for elem_info in elements:
                    text = elem_info['text']
                    data_type = classify_text(text)
                    
                    key = f"{field_type}_{elem_info['class'][:20]}"  # Limit key length
                    if key not in data_types:
                        data_types[key] = []
                    data_types[key].append(data_type)
    
    # Summarize most common data type for each field
    summary = {}
    for key, types in data_types.items():
        most_common = Counter(types).most_common(1)[0][0]
        summary[key] = most_common
    
    return summary

def classify_text(text):
    """
    Classify text into categories
    """
    text = text.lower().strip()
    
    # Price patterns
    if re.search(r'[\$€£¥₹]\s*\d+|^\d+[\.\,]\d+\s*[\$€£¥₹]?$', text):
        return 'price'
    
    # Rating patterns
    if re.search(r'\d+[\.\,]\d*\s*[/★⭐]|\d+\s*star|rating', text):
        return 'rating'
    
    # Date patterns
    if re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}', text):
        return 'date'
    
    # Title/Name (longer text, likely headings)
    if len(text) > 10 and len(text) < 100:
        return 'title/name'
    
    # Description (longer text)
    if len(text) > 50:
        return 'description'
    
    # Short text
    if len(text) < 20:
        return 'label/tag'
    
    return 'text'

def display_detected_patterns(patterns):
    """
    Display detected patterns to user for selection
    """
    if not patterns:
        print("❌ No scrapeable patterns detected on this website.")
        return None
    
    print("\n" + "="*60)
    print("🔍 DETECTED SCRAPEABLE PATTERNS")
    print("="*60)
    
    for i, (pattern_name, info) in enumerate(patterns.items(), 1):
        print(f"\n[{i}] {pattern_name}")
        print(f"    Selector: {info['selector']}")
        print(f"    Found: {info['count']} similar elements")
        
        # Show sample data
        if info['sample_data']:
            print("    Sample content preview:")
            sample = info['sample_data'][0]  # First sample
            for field_type, elements in sample.items():
                if elements:
                    element = elements[0]  # First element of each type
                    preview = element['text'][:50] + "..." if len(element['text']) > 50 else element['text']
                    print(f"      • {field_type}: '{preview}'")
    
    print("\n" + "="*60)
    return patterns

def get_user_selection(patterns):
    """
    Get user's selection of pattern and fields to scrape
    """
    pattern_list = list(patterns.keys())
    
    while True:
        try:
            choice = input(f"\nSelect pattern to scrape (1-{len(pattern_list)}) or 'q' to quit: ").strip()
            
            if choice.lower() == 'q':
                return None, None
            
            pattern_idx = int(choice) - 1
            if 0 <= pattern_idx < len(pattern_list):
                selected_pattern = pattern_list[pattern_idx]
                break
            else:
                print("❌ Invalid selection. Please try again.")
        except ValueError:
            print("❌ Please enter a valid number or 'q' to quit.")
    
    # Show available fields for selected pattern
    pattern_info = patterns[selected_pattern]
    print(f"\n📋 Available fields in {selected_pattern}:")
    
    available_fields = {}
    field_counter = 1
    
    if pattern_info['sample_data']:
        sample = pattern_info['sample_data'][0]
        for field_type, elements in sample.items():
            if elements:
                for elem_info in elements:
                    field_key = f"{field_type}_{elem_info['class'][:15]}"
                    field_preview = elem_info['text'][:40] + "..." if len(elem_info['text']) > 40 else elem_info['text']
                    
                    print(f"[{field_counter}] {field_key}")
                    print(f"    Preview: '{field_preview}'")
                    print(f"    Selector: {elem_info['selector']}")
                    
                    available_fields[field_counter] = {
                        'name': field_key,
                        'selector': elem_info['selector'],
                        'preview': field_preview
                    }
                    field_counter += 1
    
    # Let user select which fields to scrape
    print(f"\nSelect fields to scrape (comma-separated, e.g., 1,3,5) or 'all': ")
    field_selection = input().strip()
    
    selected_fields = {}
    if field_selection.lower() == 'all':
        selected_fields = available_fields
    else:
        try:
            selected_nums = [int(x.strip()) for x in field_selection.split(',')]
            for num in selected_nums:
                if num in available_fields:
                    selected_fields[num] = available_fields[num]
        except ValueError:
            print("❌ Invalid selection. Selecting all fields.")
            selected_fields = available_fields
    
    return pattern_info, selected_fields

def scrape_selected_data(url, container_selector, selected_fields, max_items=50, use_proxy=False, proxy=None):
    """
    Scrape data based on user's selection with proxy support
    """
    # Setup proxy if needed
    if use_proxy and not proxy:
        proxies = get_free_proxies()
        if proxies:
            proxy = get_working_proxy(proxies)
    
    driver = setup_driver(headless=False, use_proxy=use_proxy, proxy=proxy)
    scraped_data = []
    
    try:
        logging.info(f"🚀 Starting scraping: {url}")
        driver.get(url)
        time.sleep(random.uniform(3, 6))
        
        # Close any popups
        close_popups(driver)
        
        # Wait for containers to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, container_selector))
        )
        
        containers = driver.find_elements(By.CSS_SELECTOR, container_selector)
        logging.info(f"📦 Found {len(containers)} items to scrape")
        
        for i, container in enumerate(containers[:max_items]):
            item_data = {}
            
            for field_id, field_info in selected_fields.items():
                field_name = field_info['name']
                field_selector = field_info['selector']
                
                try:
                    # Try to find element within container
                    element = container.find_element(By.CSS_SELECTOR, field_selector)
                    item_data[field_name] = element.text.strip()
                except:
                    item_data[field_name] = "N/A"
            
            scraped_data.append(item_data)
            
            # Show progress
            if (i + 1) % 10 == 0:
                print(f"✅ Scraped {i + 1} items...")
            
            # Random delay to avoid being blocked
            if i > 0 and i % 20 == 0:
                time.sleep(random.uniform(2, 4))
        
        logging.info(f"✅ Successfully scraped {len(scraped_data)} items")
    
    except Exception as e:
        logging.error(f"❌ Scraping failed: {e}")
    finally:
        driver.quit()
    
    return scraped_data

def get_scraping_settings():
    """
    Get user preferences for scraping settings
    """
    print("\n⚙️  SCRAPING SETTINGS")
    print("="*40)
    
    # Proxy settings
    use_proxy = input("🔒 Use proxy for scraping? (y/n, default: n): ").strip().lower()
    use_proxy = use_proxy == 'y'
    
    # Headless mode
    headless = input("👻 Run in headless mode? (y/n, default: n): ").strip().lower()
    headless = headless == 'y'
    
    # Max items
    try:
        max_items = int(input("📊 How many items to scrape? (default: 50): ") or "50")
    except ValueError:
        max_items = 50
    
    # Delays
    try:
        delay = float(input("⏱️  Delay between requests (seconds, default: 3): ") or "3")
    except ValueError:
        delay = 3
    
    return {
        'use_proxy': use_proxy,
        'headless': headless,
        'max_items': max_items,
        'delay': delay
    }

def interactive_scraper():
    """
    Main interactive scraper function with proxy support
    """
    print("🕷️  INTERACTIVE WEB SCRAPER WITH PROXY SUPPORT")
    print("="*60)
    
    # Global proxy for session
    session_proxy = None
    
    while True:
        url = input("\n🌐 Enter website URL to analyze (or 'quit' to exit): ").strip()
        
        if url.lower() == 'quit':
            print("👋 Goodbye!")
            break
        
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Get scraping settings
        settings = get_scraping_settings()
        
        # Setup proxy for this session if requested
        if settings['use_proxy'] and not session_proxy:
            print("\n🔄 Setting up proxy...")
            proxies = get_free_proxies()
            if proxies:
                session_proxy = get_working_proxy(proxies)
                if session_proxy:
                    print(f"✅ Proxy ready: {session_proxy}")
                else:
                    print("⚠️ No working proxy found, continuing without proxy")
                    settings['use_proxy'] = False
            else:
                print("❌ Failed to fetch proxies, continuing without proxy")
                settings['use_proxy'] = False
        
        # Analyze website structure
        print("\n🔄 Analyzing website structure...")
        detected_patterns = analyze_website_structure(url, use_proxy=settings['use_proxy'])
        
        # Display patterns to user
        patterns = display_detected_patterns(detected_patterns)
        
        if not patterns:
            continue
        
        # Get user selection
        selected_pattern, selected_fields = get_user_selection(patterns)
        
        if not selected_pattern or not selected_fields:
            continue
        
        # Start scraping with settings
        print(f"\n🚀 Starting scrape with settings:")
        print(f"   📊 Max items: {settings['max_items']}")
        print(f"   🔒 Using proxy: {'Yes' if settings['use_proxy'] else 'No'}")
        print(f"   👻 Headless: {'Yes' if settings['headless'] else 'No'}")
        print(f"   ⏱️  Delay: {settings['delay']}s")
        
        scraped_data = scrape_selected_data(
            url, 
            selected_pattern['selector'], 
            selected_fields, 
            max_items=settings['max_items'],
            use_proxy=settings['use_proxy'],
            proxy=session_proxy
        )
        
        if scraped_data:
            # Save data
            filename = input("\n💾 Enter filename to save (default: scraped_data.csv): ").strip() or "scraped_data.csv"
            if not filename.endswith('.csv'):
                filename += '.csv'
            
            df = pd.DataFrame(scraped_data)
            df.to_csv(filename, index=False, encoding='utf-8')
            
            print(f"\n✅ SUCCESS! Scraped {len(scraped_data)} items")
            print(f"📁 Data saved to: {filename}")
            print(f"📊 Columns: {list(df.columns)}")
            
            # Show preview
            print("\n👀 Preview (first 3 rows):")
            print(df.head(3).to_string())
            
            # Show statistics
            print(f"\n📈 STATISTICS:")
            print(f"   Total items: {len(scraped_data)}")
            print(f"   Columns: {len(df.columns)}")
            print(f"   Proxy used: {'Yes' if settings['use_proxy'] else 'No'}")
            
            # Check for common issues
            null_counts = df.isnull().sum()
            if null_counts.sum() > 0:
                print(f"   Missing data: {null_counts.sum()} total nulls")
        else:
            print("\n❌ No data was scraped. Possible reasons:")
            print("   • Website blocking requests")
            print("   • Selectors changed")
            print("   • Network issues")
            print("   • Try using proxy or different settings")
        
        # Ask if user wants to continue
        continue_choice = input("\n🔄 Scrape another website? (y/n): ").strip().lower()
        if continue_choice != 'y':
            print("👋 Happy scraping!")
            break

if __name__ == "__main__":
    interactive_scraper()