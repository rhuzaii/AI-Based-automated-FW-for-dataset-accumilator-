import os
import time
import requests
import shutil
from tqdm import tqdm
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from utils.license_check import is_allowed_source
from utils.hasher import file_hash
from scraper_config import CATEGORY_MAP

class UniversalScraper:

    def __init__(self):
        # RAW DATA FOLDER
        self.raw_path = "datasets/raw_incoming"
        os.makedirs(self.raw_path, exist_ok=True)
        self.hashes = set()

    def _setup_driver(self):
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-blink-features=AutomationControlled") 
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        # Anti-detection
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'})
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver

    def _collect_image_urls(self, driver, target_urls, total_target):
        candidate_urls = []
        target_buffer = int(total_target * 1.2) 
        for start_url in target_urls:
            if len(candidate_urls) >= target_buffer:
                print(f"[SUCCESS] Hit mining target ({len(candidate_urls)})! Stopping search.")
                break
            current_url = start_url
            # print(f"\n   >>> Scanning Category: {start_url}")
            page_num = 1
            max_pages_per_category = 15
            
            while page_num <= max_pages_per_category:
                if len(candidate_urls) >= target_buffer: break

                try:
                    driver.get(current_url)
                    time.sleep(3)
                    
                    # Aggressive Scroll
                    for _ in range(3):
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(1.5)
                    
                    # Find Images
                    images = driver.find_elements(By.TAG_NAME, "img")
                    page_found_count = 0
                    
                    for img in images:
                        if len(candidate_urls) >= target_buffer: break 
                        
                        src = img.get_attribute('data-src') or img.get_attribute('src')
                        if src and "http" in src:
                            if "icon" in src or "logo" in src or "avatar" in src: continue
                            
                            if src not in candidate_urls:
                                candidate_urls.append(src)
                                page_found_count += 1
                    
                    print(f"      -> Page {page_num}: Found {page_found_count} new images. (Total: {len(candidate_urls)}/{target_buffer})")
                    
                    if page_found_count == 0:
                        print("      [WARN] No images found on this page. Moving to next category.")
                        break

                    # --- PAGINATION LOGIC ---
                    next_link = None
                    try:
                        selectors = ["li.next a", "a.next", "a[rel='next']", ".pagination a:last-child", "button.load-more"]
                        for sel in selectors:
                            try:
                                btn = driver.find_element(By.CSS_SELECTOR, sel)
                                next_link = btn.get_attribute("href")
                                if next_link: break
                            except:
                                continue
                        
                        if next_link and next_link != current_url:
                            current_url = next_link
                            page_num += 1
                        else:
                           
                            if "?" not in start_url:
                                page_num += 1
                                current_url = f"{start_url}/{page_num}"
                            else:
                                break 
                    except:
                        break
                
                except Exception as e:
                    print(f"      [WARN] Error on page: {e}")
                    break
                    
        unique_urls = list(set(candidate_urls))
        print(f"\n Found {len(unique_urls)} images.")
        return unique_urls

    def run(self, category_choice="events", total_target=500):
        target_list = CATEGORY_MAP.get(category_choice.lower())
        
        if not target_list:
            print(f"[ERR] Invalid category '{category_choice}'. Check 'scraper_config.py'.")
            return

        print(f"--- STARTING UNIVERSAL SCRAPER ({category_choice.upper()}) ---")
        
        driver = self._setup_driver()
        try:
            image_urls = self._collect_image_urls(driver, target_list, total_target)
        finally:
            driver.quit()

        print(f" Downloading images to '{self.raw_path}'...")
        count = 0
        
        # Reduced max download limit
        download_limit = int(total_target * 1.2)
        pbar = tqdm(total=min(len(image_urls), download_limit))
        
        for url in image_urls:
            if count >= download_limit: break
            
            try:
                 if not is_allowed_source(url): continue
            except:
                 pass

            try:
                r = requests.get(url, timeout=5)
                content = r.content
                
                if len(content) < 25 * 1024: continue

                h = file_hash(content)
                if h in self.hashes: continue
                self.hashes.add(h)

                filename = f"raw_{int(time.time())}_{count}.jpg"
                with open(f"{self.raw_path}/{filename}", "wb") as f:
                    f.write(content)

                count += 1
                pbar.update(1)
            except:
                continue

        pbar.close()
        print(f"\n[DONE] Downloaded {count} Raw Images.")
        print("NEXT: Run 'ai_pipeline_manager.py' to validate and categorize them.")

if __name__ == "__main__":
    scraper = UniversalScraper()
    
    print("Select Category to Scrape:")
    print("1. Events")
    print("2. Coupons")
    print("3. Gallery")
    print("4. Boarding Passes")
    
    choice = input("Enter number (1-4): ")
    
    if choice == "1":
        scraper.run("events", total_target=500)
    elif choice == "2":
        scraper.run("coupons", total_target=500)
    elif choice == "3":
        scraper.run("gallery", total_target=500)
    elif choice == "4":
        scraper.run("boarding_pass", total_target=500)
    else:
        print("Invalid choice.")