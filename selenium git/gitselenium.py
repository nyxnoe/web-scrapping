import csv
import time
import re
from datetime import datetime
from typing import List, Dict
import getpass
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import os
import sys

class EnhancedGitHubScraper:
    def __init__(self, driver_path: str = None, browser_path: str = None):
        """Initialize the enhanced GitHub scraper"""
        # Auto-detect paths if not provided
        self.driver_path = driver_path or self._detect_chromedriver_path()
        self.browser_path = browser_path or self._detect_browser_path()
        self.driver = None
        self.is_logged_in = False
        self.username = None
        self.progress_callback = None
        
    def _detect_chromedriver_path(self):
        """Auto-detect ChromeDriver path"""
        common_paths = [
            "chromedriver.exe",
            "chromedriver",
            r"C:\chromedriver\chromedriver.exe",
            r"C:\Program Files\ChromeDriver\chromedriver.exe",
            "/usr/local/bin/chromedriver",
            "/usr/bin/chromedriver"
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        # Fallback to the original path
        return r"C:\Users\nihal\OneDrive\Desktop\web scrapping\137.0.7151.68 chromedriver-win64\chromedriver-win64\chromedriver.exe"
    
    def _detect_browser_path(self):
        """Auto-detect browser path"""
        common_paths = [
            r"C:\Users\nihal\AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe",
            r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
            r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        # Fallback to original path
        return r"C:\Users\nihal\AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe"
        
    def setup_driver(self):
        """Setup Chrome WebDriver with enhanced options"""
        try:
            print("🔧 Setting up WebDriver...")
            
            options = Options()
            
            # Use Chrome if Brave is not available
            if os.path.exists(self.browser_path):
                options.binary_location = self.browser_path
                print(f"📍 Using browser: {self.browser_path}")
            else:
                print("📍 Using default Chrome browser")
            
            # Enhanced options for better stability
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-plugins')
            options.add_argument('--disable-images')  # Speed up loading
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # Add window size for better element detection
            options.add_argument('--window-size=1920,1080')
            
            service = Service(executable_path=self.driver_path)
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            print("✅ WebDriver setup successful")
            print(f"📍 ChromeDriver: {self.driver_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error setting up WebDriver: {e}")
            print("💡 Please check your ChromeDriver and browser paths")
            return False
    
    def login_to_github(self):
        """Enhanced login with better error handling"""
        if not self.driver:
            if not self.setup_driver():
                return False
        
        print("\n🔐 GitHub Login")
        print("-" * 30)
        
        username = input("Enter your GitHub username: ").strip()
        if not username:
            print("❌ Username cannot be empty")
            return False
            
        password = getpass.getpass(f"Enter password for {username}: ")
        if not password:
            print("❌ Password cannot be empty")
            return False
        
        try:
            print(f"🌐 Opening GitHub login page...")
            self.driver.get("https://github.com/login")
            
            # Wait for page to load
            wait = WebDriverWait(self.driver, 15)
            
            print("📝 Filling login credentials...")
            
            # Fill username
            username_field = wait.until(EC.presence_of_element_located((By.ID, "login_field")))
            username_field.clear()
            username_field.send_keys(username)
            
            # Fill password
            password_field = self.driver.find_element(By.ID, "password")
            password_field.clear()
            password_field.send_keys(password)
            
            # Click login
            login_button = self.driver.find_element(By.NAME, "commit")
            login_button.click()
            
            print("⏳ Logging in...")
            time.sleep(3)
            
            # Check for 2FA
            current_url = self.driver.current_url
            if "sessions/two-factor" in current_url:
                print("🔐 Two-factor authentication detected")
                print("📱 Please complete 2FA in the browser window")
                input("✅ Press Enter after completing 2FA...")
                time.sleep(2)
            
            # Verify login success
            time.sleep(2)
            current_url = self.driver.current_url
            
            if "github.com" in current_url and "login" not in current_url:
                print("✅ Successfully logged into GitHub!")
                self.is_logged_in = True
                self.username = username
                
                # Navigate to user's repository page
                print(f"🏠 Navigating to {username}'s repositories...")
                self.driver.get(f"https://github.com/{username}?tab=repositories")
                time.sleep(2)
                
                return True
            else:
                print("❌ Login failed. Please check your credentials.")
                return False
                
        except Exception as e:
            print(f"❌ Error during login: {e}")
            return False
    
    def scrape_my_repositories(self) -> List[Dict]:
        """Enhanced repository scraping with better navigation"""
        if not self.driver or not self.is_logged_in:
            print("❌ Not logged in")
            return []
        
        repositories = []
        
        print("\n📦 Starting repository scraping...")
        print("-" * 40)
        
        # Get all repository URLs first
        repo_urls = self._get_all_repository_urls()
        
        if not repo_urls:
            print("❌ No repositories found")
            return []
        
        print(f"🎯 Found {len(repo_urls)} repositories")
        print("📊 Collecting detailed information for each repository...")
        print("-" * 40)
        
        # Process each repository
        for i, repo_url in enumerate(repo_urls, 1):
            try:
                repo_name = repo_url.split('/')[-1]
                print(f"📋 [{i}/{len(repo_urls)}] Processing: {repo_name}")
                
                # Get detailed information
                repo_data = self._get_comprehensive_repo_info(repo_url)
                
                if repo_data:
                    repositories.append(repo_data)
                    print(f"✅ [{i}/{len(repo_urls)}] Completed: {repo_name}")
                else:
                    print(f"⚠️  [{i}/{len(repo_urls)}] Failed: {repo_name}")
                
                # Add delay between requests
                if i < len(repo_urls):  # Don't wait after the last repo
                    time.sleep(2)
                    
            except Exception as e:
                print(f"❌ [{i}/{len(repo_urls)}] Error processing {repo_url}: {e}")
                continue
        
        print(f"\n🎉 Successfully scraped {len(repositories)} out of {len(repo_urls)} repositories")
        return repositories
    
    def _get_all_repository_urls(self) -> List[str]:
        """Get all repository URLs with pagination support"""
        repo_urls = []
        page = 1
        
        print("🔍 Discovering all repositories...")
        
        while True:
            try:
                url = f"https://github.com/{self.username}?tab=repositories&page={page}"
                print(f"📄 Checking page {page}...")
                
                self.driver.get(url)
                time.sleep(2)
                
                wait = WebDriverWait(self.driver, 10)
                
                try:
                    # Wait for the repository list to load
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "li[itemprop='owns'], .Box-row")))
                except TimeoutException:
                    print(f"⏰ Timeout waiting for page {page} to load")
                    break
                
                # Find repository items
                repo_items = self.driver.find_elements(By.CSS_SELECTOR, "li[itemprop='owns'], .Box-row")
                
                if not repo_items:
                    print(f"📭 No repositories found on page {page}")
                    break
                
                page_repos = 0
                for item in repo_items:
                    try:
                        # Try different selectors for repository links
                        name_link = None
                        selectors = ["h3 a", "a[href*='/" + self.username + "/']", ".f4 a"]
                        
                        for selector in selectors:
                            try:
                                name_link = item.find_element(By.CSS_SELECTOR, selector)
                                break
                            except NoSuchElementException:
                                continue
                        
                        if name_link:
                            repo_url = name_link.get_attribute('href')
                            if repo_url and repo_url not in repo_urls:
                                repo_urls.append(repo_url)
                                page_repos += 1
                                
                    except NoSuchElementException:
                        continue
                
                print(f"📋 Found {page_repos} repositories on page {page}")
                
                # Check for next page
                try:
                    next_button = self.driver.find_element(By.CSS_SELECTOR, "a[rel='next']:not([disabled])")
                    if not next_button:
                        break
                except NoSuchElementException:
                    break
                
                page += 1
                
                # Safety check to prevent infinite loops
                if page > 50:  # Adjust as needed
                    print("⚠️  Reached maximum page limit")
                    break
                
            except Exception as e:
                print(f"❌ Error getting repositories from page {page}: {e}")
                break
        
        print(f"🎯 Total repositories discovered: {len(repo_urls)}")
        return repo_urls
    
    def _get_comprehensive_repo_info(self, repo_url: str) -> Dict:
        """Get comprehensive repository information with proper navigation"""
        try:
            # Navigate to repository
            self.driver.get(repo_url)
            time.sleep(3)  # Allow page to fully load
            
            wait = WebDriverWait(self.driver, 15)
            repo_data = {}
            
            # Basic repository information
            repo_data['url'] = repo_url
            repo_data['repository_name'] = repo_url.split('/')[-1]
            repo_data['owner'] = repo_url.split('/')[-2]
            repo_data['full_name'] = f"{repo_data['owner']}/{repo_data['repository_name']}"
            
            # Wait for main content to load
            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#repository-container-header, .pagehead")))
            except TimeoutException:
                print(f"⚠️  Page load timeout for {repo_data['repository_name']}")
            
            # Get all information
            repo_data.update(self._extract_basic_info())
            repo_data.update(self._extract_statistics())
            repo_data.update(self._extract_metadata())
            repo_data.update(self._extract_content_info())
            
            return repo_data
            
        except Exception as e:
            print(f"⚠️  Error getting info for {repo_url}: {e}")
            return {}
    
    def _extract_basic_info(self) -> Dict:
        """Extract basic repository information"""
        info = {}
        
        # Description
        try:
            desc_selectors = [
                "[data-pjax='#repo-content-pjax-container'] p",
                ".f4.my-3",
                ".repository-description p"
            ]
            for selector in desc_selectors:
                try:
                    desc_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    info['description'] = desc_element.text.strip()
                    break
                except NoSuchElementException:
                    continue
            else:
                info['description'] = ""
        except:
            info['description'] = ""
        
        # Repository type flags
        info['is_fork'] = self._check_fork_status()
        info['is_private'] = self._check_private_status()
        info['is_archived'] = self._check_archived_status()
        
        return info
    
    def _extract_statistics(self) -> Dict:
        """Extract repository statistics"""
        stats = {}
        
        # Stars, Forks, Watchers
        stats['stars'] = self._get_stat_count('stargazers', 'star')
        stats['forks'] = self._get_stat_count('forks', 'fork')
        stats['watchers'] = self._get_stat_count('watchers', 'watch')
        
        # Issues and Pull Requests
        stats['open_issues'] = self._get_issues_count()
        stats['open_pull_requests'] = self._get_pull_requests_count()
        
        return stats
    
    def _extract_metadata(self) -> Dict:
        """Extract repository metadata"""
        metadata = {}
        
        # Language information
        metadata['primary_language'] = self._get_primary_language()
        metadata['languages'] = self._get_languages_info()
        
        # Topics
        metadata['topics'] = self._get_topics()
        
        # License
        metadata['license'] = self._get_license()
        
        # Dates
        metadata['created_at'] = self._get_creation_date()
        metadata['updated_at'] = self._get_last_update()
        
        return metadata
    
    def _extract_content_info(self) -> Dict:
        """Extract repository content information"""
        content = {}
        
        # README
        content['has_readme'] = self._has_readme()
        
        # File count (approximate)
        content['files_count'] = self._get_files_count()
        
        # Commits, branches, releases
        content['commits_count'] = self._get_commits_count()
        content['branches_count'] = self._get_branches_count()
        content['releases_count'] = self._get_releases_count()
        
        # Size
        content['size'] = self._get_repository_size()
        
        return content
    
    def _get_stat_count(self, stat_type: str, alt_name: str = None) -> int:
        """Get statistics count with multiple selector attempts"""
        selectors = [
            f"a[href*='/{stat_type}'] strong",
            f"a[href*='/{stat_type}'] .Counter",
            f"#{stat_type}-repo-tab-count",
            f"[data-tab-item='{stat_type}'] strong",
            f"[data-tab-item='{stat_type}'] .Counter"
        ]
        
        if alt_name:
            selectors.extend([
                f"a[href*='/{alt_name}'] strong",
                f"a[href*='/{alt_name}'] .Counter"
            ])
        
        for selector in selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                return self._parse_number(element.text.strip())
            except NoSuchElementException:
                continue
        
        return 0
    
    def _check_fork_status(self) -> bool:
        """Check if repository is a fork"""
        fork_indicators = [
            ".octicon-repo-forked",
            "[title*='fork']",
            "span:contains('forked from')"
        ]
        
        for indicator in fork_indicators:
            try:
                self.driver.find_element(By.CSS_SELECTOR, indicator)
                return True
            except NoSuchElementException:
                continue
        return False
    
    def _check_private_status(self) -> bool:
        """Check if repository is private"""
        try:
            private_indicators = self.driver.find_elements(By.CSS_SELECTOR, ".Label--secondary, .Label:contains('Private')")
            return len(private_indicators) > 0
        except:
            return False
    
    def _check_archived_status(self) -> bool:
        """Check if repository is archived"""
        try:
            self.driver.find_element(By.CSS_SELECTOR, ".flash-warn, .archived")
            return True
        except NoSuchElementException:
            return False
    
    def _get_primary_language(self) -> str:
        """Get primary programming language"""
        try:
            lang_element = self.driver.find_element(By.CSS_SELECTOR, "[itemprop='programmingLanguage']")
            return lang_element.text.strip()
        except NoSuchElementException:
            return ""
    
    def _get_languages_info(self) -> str:
        """Get language information"""
        try:
            # Try to find language bar
            lang_elements = self.driver.find_elements(By.CSS_SELECTOR, ".BorderGrid-row .BorderGrid-cell .Progress-item")
            languages = []
            
            for element in lang_elements:
                try:
                    lang_name = element.get_attribute('aria-label')
                    if lang_name:
                        lang_name = lang_name.split()[0]  # Get just the language name
                        if lang_name not in languages:
                            languages.append(lang_name)
                except:
                    continue
            
            return ", ".join(languages) if languages else ""
        except:
            return ""
    
    def _get_topics(self) -> str:
        """Get repository topics"""
        try:
            topic_elements = self.driver.find_elements(By.CSS_SELECTOR, ".topic-tag, .topic-tag-link")
            topics = [topic.text.strip() for topic in topic_elements if topic.text.strip()]
            return ", ".join(topics)
        except:
            return ""
    
    def _get_license(self) -> str:
        """Get repository license"""
        try:
            license_selectors = [
                ".octicon-law + span",
                "a[href*='/blob/'] .octicon-law + span",
                ".license .Link--primary"
            ]
            
            for selector in license_selectors:
                try:
                    license_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    return license_element.text.strip()
                except NoSuchElementException:
                    continue
            return ""
        except:
            return ""
    
    def _get_creation_date(self) -> str:
        """Get repository creation date"""
        try:
            date_element = self.driver.find_element(By.CSS_SELECTOR, "relative-time")
            return date_element.get_attribute('datetime')
        except NoSuchElementException:
            return ""
    
    def _get_last_update(self) -> str:
        """Get last update date"""
        try:
            update_elements = self.driver.find_elements(By.CSS_SELECTOR, "relative-time")
            if len(update_elements) > 1:
                return update_elements[-1].get_attribute('datetime')
            elif update_elements:
                return update_elements[0].get_attribute('datetime')
            return ""
        except:
            return ""
    
    def _has_readme(self) -> bool:
        """Check if repository has README"""
        try:
            readme_selectors = [
                "[data-testid='readme']",
                "#readme",
                ".Box-header h2:contains('README')"
            ]
            
            for selector in readme_selectors:
                try:
                    self.driver.find_element(By.CSS_SELECTOR, selector)
                    return True
                except NoSuchElementException:
                    continue
            return False
        except:
            return False
    
    def _get_files_count(self) -> int:
        """Get files count from directory listing"""
        try:
            file_rows = self.driver.find_elements(By.CSS_SELECTOR, "[role='rowgroup'] [role='row'], .js-navigation-item")
            # Subtract 1 for header row if present
            count = len(file_rows)
            return max(0, count - 1) if count > 0 else 0
        except:
            return 0
    
    def _get_commits_count(self) -> int:
        """Get commits count"""
        selectors = [
            "a[href*='/commits'] strong",
            ".octicon-history ~ strong",
            "[data-tab-item='commits'] strong"
        ]
        
        for selector in selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                return self._parse_number(element.text.strip())
            except NoSuchElementException:
                continue
        return 0
    
    def _get_branches_count(self) -> int:
        """Get branches count"""
        try:
            branches_element = self.driver.find_element(By.CSS_SELECTOR, "a[href*='/branches'] strong")
            return self._parse_number(branches_element.text.strip())
        except NoSuchElementException:
            return 0
    
    def _get_releases_count(self) -> int:
        """Get releases count"""
        try:
            releases_element = self.driver.find_element(By.CSS_SELECTOR, "a[href*='/releases'] strong")
            return self._parse_number(releases_element.text.strip())
        except NoSuchElementException:
            return 0
    
    def _get_issues_count(self) -> int:
        """Get open issues count"""
        try:
            issues_element = self.driver.find_element(By.CSS_SELECTOR, "a[href*='/issues'] .Counter")
            return self._parse_number(issues_element.text.strip())
        except NoSuchElementException:
            return 0
    
    def _get_pull_requests_count(self) -> int:
        """Get open pull requests count"""
        try:
            pr_element = self.driver.find_element(By.CSS_SELECTOR, "a[href*='/pulls'] .Counter")
            return self._parse_number(pr_element.text.strip())
        except NoSuchElementException:
            return 0
    
    def _get_repository_size(self) -> str:
        """Get repository size"""
        try:
            size_selectors = [
                ".file-navigation .text-small",
                ".Box-header .text-small"
            ]
            
            for selector in size_selectors:
                try:
                    size_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    size_text = size_element.text
                    if any(unit in size_text for unit in ["MB", "KB", "GB", "bytes"]):
                        return size_text.strip()
                except NoSuchElementException:
                    continue
            return ""
        except:
            return ""
    
    def _parse_number(self, text: str) -> int:
        """Parse number from text like '1.2k' or '1,234'"""
        try:
            if not text:
                return 0
            
            # Remove commas
            text = text.replace(',', '').strip()
            
            # Handle k, m suffixes
            if text.lower().endswith('k'):
                return int(float(text[:-1]) * 1000)
            elif text.lower().endswith('m'):
                return int(float(text[:-1]) * 1000000)
            else:
                # Extract numbers only
                numbers = re.findall(r'\d+\.?\d*', text)
                if numbers:
                    return int(float(numbers[0]))
                return 0
        except:
            return 0
    
    def export_to_csv(self, repos_data: List[Dict], filename: str = None):
        """Export repository data to CSV with enhanced formatting"""
        if not repos_data:
            print("❌ No data to export")
            return None
        
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"github_repositories_{self.username}_{timestamp}.csv"
        
        try:
            fieldnames = [
                'repository_name', 'full_name', 'owner', 'description', 'url',
                'primary_language', 'languages', 'stars', 'forks', 'watchers',
                'commits_count', 'branches_count', 'releases_count', 'files_count',
                'is_fork', 'is_private', 'is_archived', 'has_readme',
                'created_at', 'updated_at', 'size', 'topics', 'license',
                'open_issues', 'open_pull_requests'
            ]
            
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for repo in repos_data:
                    # Ensure all fields exist with default values
                    row = {}
                    for field in fieldnames:
                        value = repo.get(field, '')
                        # Convert boolean values to readable text
                        if isinstance(value, bool):
                            row[field] = 'Yes' if value else 'No'
                        else:
                            row[field] = value
                    writer.writerow(row)
            
            print(f"💾 Successfully exported {len(repos_data)} repositories to: {filename}")
            return filename
            
        except Exception as e:
            print(f"❌ Error exporting to CSV: {e}")
            return None
    
    def print_summary(self, repos_data: List[Dict]):
        """Print detailed summary of scraped repositories"""
        if not repos_data:
            return
        
        print("\n" + "="*60)
        print("📊 SCRAPING SUMMARY")
        print("="*60)
        
        # Basic counts
        total_repos = len(repos_data)
        public_repos = len([r for r in repos_data if not r.get('is_private', False)])
        private_repos = len([r for r in repos_data if r.get('is_private', False)])
        forked_repos = len([r for r in repos_data if r.get('is_fork', False)])
        archived_repos = len([r for r in repos_data if r.get('is_archived', False)])
        
        print(f"👤 User: {self.username}")
        print(f"📦 Total repositories: {total_repos}")
        print(f"🌍 Public repositories: {public_repos}")
        print(f"🔒 Private repositories: {private_repos}")
        print(f"🍴 Forked repositories: {forked_repos}")
        print(f"📦 Archived repositories: {archived_repos}")
        
        # Statistics
        total_stars = sum(r.get('stars', 0) for r in repos_data)
        total_forks = sum(r.get('forks', 0) for r in repos_data)
        total_watchers = sum(r.get('watchers', 0) for r in repos_data)
        
        print(f"\n⭐ Total stars: {total_stars:,}")
        print(f"🍴 Total forks: {total_forks:,}")
        print(f"👀 Total watchers: {total_watchers:,}")
        
        # Language analysis
        languages = {}
        for repo in repos_data:
            lang = repo.get('primary_language', '').strip()
            if lang and lang.lower() != 'none':
                languages[lang] = languages.get(lang, 0) + 1
        
        if languages:
            print(f"\n🔤 Programming Languages:")
            sorted_langs = sorted(languages.items(), key=lambda x: x[1], reverse=True)
            for lang, count in sorted_langs[:10]:  # Top 10
                print(f"   {lang}: {count} repositories")
        
        # Repository with most stars
        if total_stars > 0:
            most_starred = max(repos_data, key=lambda x: x.get('stars', 0))
            print(f"\n🌟 Most starred repository:")
            print(f"   {most_starred['repository_name']} ({most_starred.get('stars', 0)} stars)")
        
        print("="*60)
    
    def close(self):
        """Close the WebDriver safely"""
        if self.driver:
            try:
                self.driver.quit()
                print("🔒 Browser closed successfully")
            except:
                print("🔒 Browser session ended")

def main():
    """Enhanced main function with better user experience"""
    print("🚀 Enhanced GitHub Repository Scraper")
    print("="*50)
    print("This tool will:")
    print("• Login to your GitHub account")
    print("• Discover all your repositories")
    print("• Extract detailed information from each repo")
    print("• Export everything to a CSV file")
    print("• Provide a detailed summary of your repositories")
    print("="*50)
    scraper = EnhancedGitHubScraper()

    if scraper.login_to_github():
        repos = scraper.scrape_my_repositories()
        if repos:
            scraper.print_summary(repos)
            scraper.export_to_csv(repos)
    else:
        print("❌ Unable to login to GitHub. Please check your credentials or complete 2FA.")

    scraper.close()

if __name__ == "__main__":
    main()