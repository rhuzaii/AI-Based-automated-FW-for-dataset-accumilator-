import os
import time
import requests
import shutil
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from utils.license_check import is_allowed_source
from utils.hasher import file_hash

class UniversalScraper:
    def __init__(self):
        # STAGE 1 OUTPUT: Processed Raw Data (Unsorted)
        self.raw_path = "datasets/raw_incoming"
        os.makedirs(self.raw_path, exist_ok=True)
        self.hashes = set()

    def _setup_driver(self):
        options = Options()
        # options.add_argument("--headless") # Un-comment to run hidden
        options.add_argument("--disable-gpu")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36")
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)

    def scrape_website(self, url, max_images=50):
        print(f"\n[STAGE 1] Scraping: {url}")
        
        # 1. License Check
        if not is_allowed_source(url):
            print(f"[BLOCK] URL not in allowed list (Ethical Compliance Check Failed).")
            return

        driver = self._setup_driver()
        try:
            driver.get(url)
            time.sleep(3)
            
            # Scroll to load content
            for _ in range(3):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
            
            # Find ALL images (Generic Collection)
            images = driver.find_elements(By.TAG_NAME, "img")
            print(f"[INFO] Found {len(images)} potential images.")
            
            count = 0
            for img in images:
                if count >= max_images: break
                
                src = img.get_attribute('src') or img.get_attribute('data-src')
                
                if src and "http" in src:
                    try:
                        # Download
                        r = requests.get(src, timeout=5)
                        content = r.content
                        
                        # Pre-processing: Dedup check (Hash)
                        h = file_hash(content)
                        if h in self.hashes: continue
                        self.hashes.add(h)
                        
                        # Save to Raw Folder
                        filename = f"raw_{int(time.time())}_{count}.jpg"
                        with open(f"{self.raw_path}/{filename}", "wb") as f:
                            f.write(content)
                        
                        count += 1
                    except:
                        continue
                        
            print(f"[SUCCESS] Downloaded {count} raw images to '{self.raw_path}'")
            
        finally:
            driver.quit()

if __name__ == "__main__":
    scraper = UniversalScraper()
    # Ask user for input
    target = input("Enter website URL to scrape: ")
    scraper.scrape_website(target)