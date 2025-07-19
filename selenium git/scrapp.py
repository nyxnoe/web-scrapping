from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time
import requests
from bs4 import BeautifulSoup
import random
import logging
from urllib.parse import quote
import os

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_free_proxies():
    """Fetch free proxies from free-proxy-list.net"""
    try:
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
        
        logging.info(f"Found {len(proxies)} HTTPS proxies")
        return proxies
    except Exception as e:
        logging.error(f"Failed to fetch proxies: {e}")
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
    random.shuffle(proxies)
    for i, proxy in enumerate(proxies[:max_attempts]):
        logging.info(f"Testing proxy {i+1}/{max_attempts}: {proxy}")
        if test_proxy(proxy):
            logging.info(f"✅ Working proxy found: {proxy}")
            return proxy
        else:
            logging.warning(f"❌ Proxy failed: {proxy}")
    
    logging.warning("No working proxies found, continuing without proxy...")
    return None

def setup_driver(proxy=None, headless=False):
    """Setup Chrome driver with options"""
    chrome_driver_path = r"C:\Users\nihal\OneDrive\Desktop\web scrapping\137.0.7151.68 chromedriver-win64\chromedriver-win64\chromedriver.exe"
    brave_path = r"C:\Users\nihal\AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe"
    
    options = Options()
    options.binary_location = brave_path
    
    # Basic options
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-extensions")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    if headless:
        options.add_argument("--headless")
    
    if proxy:
        options.add_argument(f'--proxy-server={proxy}')
    
    # User agent
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    options.add_argument(f"--user-agent={user_agent}")
    
    service = Service(executable_path=chrome_driver_path)
    driver = webdriver.Chrome(service=service, options=options)
    
    # Execute script to remove webdriver property
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

def close_popups(driver):
    """Close any popups that might appear"""
    popup_selectors = [
        "//button[contains(@class, '_2KpZ6l')]",  # Login popup close
        "//span[text()='✕']",  # Generic close button
        "//button[text()='✕']",  # Generic close button
        "//*[@class='_3Njdz7']",  # Another popup close
        "//button[contains(text(), 'Later')]",  # Later button
        "//span[contains(@role, 'button') and contains(text(), '✕')]"
    ]
    
    for selector in popup_selectors:
        try:
            element = WebDriverWait(driver, 2).until(
                EC.element_to_be_clickable((By.XPATH, selector))
            )
            element.click()
            logging.info(f"Closed popup with selector: {selector}")
            time.sleep(1)
            break  # Exit after first successful close
        except:
            continue

def debug_page_structure(driver, debug_mode=True):
    """Debug function to understand current page structure"""
    if not debug_mode:
        return
    
    try:
        # Take screenshot for debugging
        screenshot_path = "flipkart_debug.png"
        driver.save_screenshot(screenshot_path)
        logging.info(f"Screenshot saved: {screenshot_path}")
        
        # Print page title
        logging.info(f"Page title: {driver.title}")
        
        # Print current URL
        logging.info(f"Current URL: {driver.current_url}")
        
        # Check for common product container selectors
        test_selectors = [
            "[data-id]",
            "._1AtVbE",
            "._13oc-S",
            "._2kHMtA",
            "._1fQZEK",
            ".s1Q9rs",
            "._4rR01T",
            ".IRpwTa",
            "._2WkVRV",
            "._1YokD2",
            "._3pLy-c"
        ]
        
        for selector in test_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    logging.info(f"Found {len(elements)} elements with selector: {selector}")
                    if len(elements) > 0:
                        sample_text = elements[0].text.strip()[:100] if elements[0].text else "No text"
                        logging.info(f"Sample text: {sample_text}")
            except Exception as e:
                logging.debug(f"Error testing selector {selector}: {e}")
        
        # Save page source for manual inspection
        with open("flipkart_page_source.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        logging.info("Page source saved to flipkart_page_source.html")
        
    except Exception as e:
        logging.error(f"Debug error: {e}")

def scrape_flipkart_updated(keyword, max_pages=1, use_proxy=False, debug_mode=True):
    """Updated scraping function with better selectors"""
    logging.info(f"Starting scrape for keyword: {keyword}")
    
    # Get proxies if needed
    proxy = None
    if use_proxy:
        proxies = get_free_proxies()
        if proxies:
            proxy = get_working_proxy(proxies)
    
    # Setup driver
    driver = setup_driver(proxy)
    
    all_product_data = []
    
    try:
        for page in range(1, max_pages + 1):
            logging.info(f"Scraping page {page}/{max_pages}")
            
            # Construct URL
            if page == 1:
                url = f"https://www.flipkart.com/search?q={quote(keyword)}"
            else:
                url = f"https://www.flipkart.com/search?q={quote(keyword)}&page={page}"
            
            logging.info(f"Navigating to: {url}")
            driver.get(url)
            
            # Wait for page to load
            time.sleep(random.uniform(3, 6))
            
            # Close popups
            close_popups(driver)
            
            # Debug page structure
            if debug_mode:
                debug_page_structure(driver, debug_mode)
            
            # Try multiple approaches to find products
            product_data = []
            
            # Approach 1: Look for main product containers
            container_selectors = [
                "._1AtVbE",  # Old selector
                "._2kHMtA",  # Another container
                "._13oc-S",  # Product row
                ".s1Q9rs",   # Product name direct
                "._3pLy-c",  # Grid container
                "[data-id]"  # Data attribute
            ]
            
            products_found = False
            for container_selector in container_selectors:
                try:
                    containers = driver.find_elements(By.CSS_SELECTOR, container_selector)
                    if containers:
                        logging.info(f"Found {len(containers)} containers with: {container_selector}")
                        
                        for i, container in enumerate(containers[:20]):  # Limit to first 20
                            try:
                                # Extract product name
                                name_selectors = [
                                    ".s1Q9rs",
                                    "._4rR01T", 
                                    ".IRpwTa",
                                    "a[title]",
                                    ".KzDlHZ",
                                    "._2WkVRV .IRpwTa",
                                    ".col-7-12 ._4rR01T"
                                ]
                                
                                product_name = None
                                for name_sel in name_selectors:
                                    try:
                                        name_elem = container.find_element(By.CSS_SELECTOR, name_sel)
                                        product_name = name_elem.get_attribute("title") or name_elem.text.strip()
                                        if product_name and len(product_name) > 5:
                                            break
                                    except:
                                        continue
                                
                                # Extract price
                                price_selectors = [
                                    "._30jeq3",
                                    "._1_WHN1", 
                                    ".Nx9bqj",
                                    "._3I9_wc",
                                    ".CEmiEU"
                                ]
                                
                                product_price = None
                                for price_sel in price_selectors:
                                    try:
                                        price_elem = container.find_element(By.CSS_SELECTOR, price_sel)
                                        product_price = price_elem.text.strip()
                                        if product_price and '₹' in product_price:
                                            break
                                    except:
                                        continue
                                
                                # Extract rating
                                rating = None
                                try:
                                    rating_elem = container.find_element(By.CSS_SELECTOR, "._3LWZlK, ._2d4LTz")
                                    rating = rating_elem.text.strip()
                                except:
                                    pass
                                
                                if product_name and product_price:
                                    product_data.append({
                                        'Product': product_name,
                                        'Price': product_price,
                                        'Rating': rating or 'N/A',
                                        'Page': page,
                                        'Container': container_selector
                                    })
                                    products_found = True
                                    
                                    if debug_mode and i < 3:  # Log first 3 products for debugging
                                        logging.info(f"Product {i+1}: {product_name[:50]} - {product_price}")
                            
                            except Exception as e:
                                if debug_mode:
                                    logging.debug(f"Error extracting from container {i}: {e}")
                                continue
                        
                        if products_found:
                            break  # Use first working selector
                            
                except Exception as e:
                    logging.debug(f"Error with container selector {container_selector}: {e}")
                    continue
            
            if not products_found:
                logging.warning(f"No products found on page {page}")
                if debug_mode:
                    # Try to find any clickable elements that might be products
                    all_links = driver.find_elements(By.TAG_NAME, "a")
                    product_links = [link for link in all_links if 'p[' in link.get_attribute('href') or '']
                    logging.info(f"Found {len(product_links)} potential product links")
            
            logging.info(f"Extracted {len(product_data)} products from page {page}")
            all_product_data.extend(product_data)
            
            # Random delay between pages
            if page < max_pages:
                time.sleep(random.uniform(3, 7))
    
    except Exception as e:
        logging.error(f"Error during scraping: {e}")
        import traceback
        logging.error(traceback.format_exc())
    
    finally:
        driver.quit()
        logging.info("Driver closed")
    
    return all_product_data

def save_to_csv(data, filename='flipkart_products.csv'):
    """Save data to CSV file"""
    if data:
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False, encoding='utf-8')
        logging.info(f"✅ Saved {len(data)} products to {filename}")
        
        # Display summary
        print(f"\n📊 SCRAPING SUMMARY:")
        print(f"Total products: {len(data)}")
        if 'Page' in df.columns:
            print(f"Pages scraped: {df['Page'].nunique()}")
        print(f"File saved: {filename}")
        
        # Show first few products
        print(f"\n🔍 SAMPLE PRODUCTS:")
        for i, row in df.head(5).iterrows():
            print(f"{i+1}. {row['Product'][:60]}... - {row['Price']}")
    else:
        logging.warning("No data to save")
        print("\n❌ NO PRODUCTS FOUND!")
        print("Check the debug files:")
        print("- flipkart_debug.png (screenshot)")
        print("- flipkart_page_source.html (page source)")

# -------- MAIN EXECUTION ----------
if __name__ == "__main__":
    # Configuration
    KEYWORD = "laptop"      # 🔍 Change this to search for different products
    MAX_PAGES = 1          # 📄 Start with 1 page for debugging
    USE_PROXY = False      # 🔒 Disable proxy for debugging
    DEBUG_MODE = True      # 🐛 Enable debug mode
    
    # Start scraping
    try:
        products = scrape_flipkart_updated(KEYWORD, MAX_PAGES, USE_PROXY, DEBUG_MODE)
        save_to_csv(products, f'flipkart_{KEYWORD.replace(" ", "_")}.csv')
    except KeyboardInterrupt:
        logging.info("Scraping interrupted by user")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        import traceback
        logging.error(traceback.format_exc())