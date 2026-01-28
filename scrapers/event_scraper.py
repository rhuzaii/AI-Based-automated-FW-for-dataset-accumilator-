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

# Import your existing utils
from utils.validator import validate_image
from utils.metadata import write_metadata
from utils.hasher import file_hash
from utils.license_check import is_allowed_source

class EventScraper:

    def __init__(self, total_target=500):
        self.category = "events"
        self.total_target = total_target
        
        self.base_path = f"datasets/{self.category}"
        self.img_path = f"{self.base_path}/images"
        self.meta_path = f"{self.base_path}/metadata.csv"
        
        # --- ROBUST CLEANUP ---
        # Try to remove the old folder, but don't crash if it's locked
        if os.path.exists(self.base_path):
            try:
                shutil.rmtree(self.base_path)
            except PermissionError:
                print(f"[WARN] Could not delete '{self.base_path}'.")
                print("       File is likely open in Excel. Appending to existing dataset instead.")
            except Exception as e:
                print(f"[WARN] Cleanup failed: {e}")

        os.makedirs(self.img_path, exist_ok=True)
        self.hashes = set()

        # --- EXPANDED CATEGORY LIST (To ensure 500+ images) ---
        self.target_urls = [
            "https://www.greetingsisland.com/invitations/professional-events",
            "https://www.greetingsisland.com/invitations/kids-birthday", 
            "https://www.greetingsisland.com/invitations/baby-shower",
            "https://www.greetingsisland.com/invitations/party",
            "https://www.greetingsisland.com/invitations/wedding",        # NEW
            "https://www.greetingsisland.com/invitations/anniversary",    # NEW
            "https://www.greetingsisland.com/invitations/graduation",     # NEW
            "https://www.greetingsisland.com/cards/birthday"              # NEW
        ]

    def _setup_driver(self):
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36")
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)

    def _collect_image_urls(self, driver):
        """Scrapes URLs using Dynamic Pagination (Finding the 'Next' button)"""
        candidate_urls = []
        target_buffer = self.total_target + 150  # Collect extra to account for duplicates
        
        print(f"[INFO] Mining URLs from {len(self.target_urls)} categories (Target Buffer: {target_buffer})...")
        
        for start_url in self.target_urls:
            if len(set(candidate_urls)) >= target_buffer:
                break
                
            current_url = start_url
            print(f"\n   [CATEGORY] Starting: {start_url}")
            
            # Scrape up to 5 pages per category
            for page_num in range(1, 6):
                try:
                    driver.get(current_url)
                    time.sleep(2)
                    
                    # 1. Scroll Aggressively (Trigger Lazy Load)
                    for _ in range(4):
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(1)
                    
                    # 2. Collect Images
                    images = driver.find_elements(By.TAG_NAME, "img")
                    page_count = 0
                    for img in images:
                        src = img.get_attribute('data-src') or img.get_attribute('src')
                        if src and "http" in src:
                             if "greetingsisland" in src or "cloudfront" in src or "amazon" in src:
                                candidate_urls.append(src)
                                page_count += 1
                    
                    print(f"      -> Page {page_num}: Found {page_count} images. (Total Unique: {len(set(candidate_urls))})")

                    # 3. Find 'Next Page' Link Dynamically
                    try:
                        # Look for a standard pagination 'Next' link
                        # Greetings Island usually uses a class like 'next' or 'pagination-next'
                        next_btn = driver.find_element(By.CSS_SELECTOR, "a.next, li.next a, a[rel='next']")
                        next_link = next_btn.get_attribute("href")
                        
                        if next_link and next_link != current_url:
                            current_url = next_link # Set URL for next loop iteration
                        else:
                            print("      [INFO] No next page found. Moving to next category.")
                            break
                    except:
                        # If we can't find a next button, try manually guessing the next page structure
                        # Some sections use /2, /3 structure
                        current_url = f"{start_url}/{page_num + 1}"
                        # print(f"      [DEBUG] Trying manual next page: {current_url}")
                
                except Exception as e:
                    print(f"      [WARN] Skipping page: {e}")
                    break
                    
        unique_urls = list(set(candidate_urls))
        print(f"\n[INFO] Mining Complete. Found {len(unique_urls)} unique candidates.")
        return unique_urls

    def run(self):
        start = time.time()
        count = 0
        
        # 1. Initialize Selenium
        driver = self._setup_driver()
        try:
            image_urls = self._collect_image_urls(driver)
        finally:
            driver.quit()

        print(f"[INFO] Starting download of {min(len(image_urls), self.total_target)} images...")

        # 2. Download Loop
        pbar = tqdm(total=self.total_target)
        
        for url in image_urls:
            if count >= self.total_target:
                break

            # License Check
            if not is_allowed_source(url):
                continue

            try:
                r = requests.get(url, timeout=10)
                content = r.content
            except:
                continue

            # Validation
            if not validate_image(content):
                continue

            # Duplicate Check
            h = file_hash(content)
            if h in self.hashes:
                continue
            self.hashes.add(h)

            # Save
            filename = f"event_{count}.jpg"
            filepath = os.path.join(self.img_path, filename)

            with open(filepath, "wb") as f:
                f.write(content)

            write_metadata(
                self.meta_path,
                [
                    filename,
                    url,
                    time.strftime("%Y-%m-%d %H:%M:%S"),
                    self.category,
                    round(len(content)/1024, 2)
                ]
            )

            count += 1
            pbar.update(1)

        pbar.close()
        end = time.time()

        print("\n====== EVENT SCRAPER REPORT ======")
        print("Total images:", count)
        print("Time:", round(end-start, 2), "seconds")
        if count > 0:
            print("Rate:", round(count/((end-start)/3600), 2), "samples/hour")
        else:
            print("Rate: 0 samples/hour")