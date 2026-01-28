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

class MixedScraper:
    def __init__(self, total_target=200):
        # DUMP EVERYTHING INTO ONE RAW FOLDER
        self.raw_path = "datasets/raw_incoming"
        
        if os.path.exists(self.raw_path):
            shutil.rmtree(self.raw_path)
        os.makedirs(self.raw_path, exist_ok=True)
        
        self.total_target = total_target
        self.hashes = set()

        # MIXED SOURCES (Coupons, Events, Gallery, Travel)
        self.target_urls = [
            # Coupons
            "https://www.grabon.in/food-dining-coupons/",
            "https://www.grabon.in/travel-coupons/",
            # Events
            "https://www.greetingsisland.com/invitations/party",
            "https://www.greetingsisland.com/invitations/wedding",
            # Gallery (Stock Photos)
            "https://unsplash.com/s/photos/people",
            "https://unsplash.com/s/photos/nature",
            # Travel (Boarding Pass samples often found on blogs - simulating generic crawl)
            "https://www.google.com/search?q=boarding+pass+template&tbm=isch" 
        ]

    def _setup_driver(self):
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36")
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)

    def run(self):
        print(f"[INFO] Starting MIXED Collection -> '{self.raw_path}'")
        driver = self._setup_driver()
        count = 0
        
        # 1. Collect URLs from all mixed sources
        candidate_urls = []
        for url in self.target_urls:
            try:
                driver.get(url)
                time.sleep(2)
                driver.execute_script("window.scrollTo(0, 1000);")
                time.sleep(2)
                
                images = driver.find_elements(By.TAG_NAME, "img")
                for img in images:
                    src = img.get_attribute('src') or img.get_attribute('data-src')
                    if src and "http" in src:
                        candidate_urls.append(src)
            except:
                continue

        driver.quit()
        unique_urls = list(set(candidate_urls))
        print(f"[INFO] Found {len(unique_urls)} mixed images. Downloading...")

        # 2. Download loop
        for url in tqdm(unique_urls):
            if count >= self.total_target: break
            
            # Basic Safety Check (Robots.txt)
            if not is_allowed_source(url): continue

            try:
                r = requests.get(url, timeout=5)
                content = r.content
                
                # Basic File Hash (Dedup)
                h = file_hash(content)
                if h in self.hashes: continue
                self.hashes.add(h)
                
                # Save as "raw_image_X" (No category info!)
                with open(f"{self.raw_path}/raw_{count}.jpg", "wb") as f:
                    f.write(content)
                count += 1
            except:
                continue
                
        print(f"[DONE] Collected {count} mixed images.")

if __name__ == "__main__":
    MixedScraper(total_target=50).run()