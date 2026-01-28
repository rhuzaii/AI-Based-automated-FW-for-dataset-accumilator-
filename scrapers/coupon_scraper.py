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

# Import Utils
from utils.validator import validate_image
from utils.metadata import write_metadata
from utils.hasher import file_hash
from utils.license_check import is_allowed_source

class CouponScraper:

    def __init__(self, total_target=500):
        self.category = "coupons"
        self.total_target = total_target
        
        self.base_path = f"datasets/{self.category}"
        self.img_path = f"{self.base_path}/images"
        self.meta_path = f"{self.base_path}/metadata.csv"
        
        # Safe Cleanup (WinError 32 fix)
        if os.path.exists(self.base_path):
            try:
                shutil.rmtree(self.base_path)
            except PermissionError:
                print(f"[WARN] Could not delete '{self.base_path}'. Appending to existing.")
            except Exception:
                pass

        os.makedirs(self.img_path, exist_ok=True)
        self.hashes = set()

        # Target Specific Brands matching your screenshots
        self.target_urls = [
            "https://www.grabon.in/mamaearth-coupons/",   # Matches your Mamaearth image
            "https://www.grabon.in/goibibo-coupons/",     # Matches your Goibibo image
            "https://www.grabon.in/cleartrip-coupons/",   # Matches your Cleartrip image
            "https://www.grabon.in/zomato-coupons/",      # Matches your NeuCard/Zomato image
            "https://www.grabon.in/urbanic-coupons/",     # Matches Urban Style
            "https://www.grabon.in/boat-coupons/",        # Matches Tech/Headphones
            "https://www.grabon.in/myntra-coupons/",
            "https://www.coupondunia.in/amazon",
            "https://www.coupondunia.in/flipkart"
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
        candidate_urls = []
        target_buffer = self.total_target + 100
        
        print(f"[INFO] Mining Coupon Banners (Target: {target_buffer})...")
        
        for url in self.target_urls:
            if len(set(candidate_urls)) >= target_buffer:
                break
                
            try:
                # print(f"   [BRAND] Visiting: {url}")
                driver.get(url)
                time.sleep(2)
                
                # Scroll to load lazy images
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
                time.sleep(1)
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)

                # --- SMART FILTER ---
                # We want "Banners" and "Deal Cards", not tiny icons.
                images = driver.find_elements(By.TAG_NAME, "img")
                
                for img in images:
                    src = img.get_attribute('data-src') or img.get_attribute('src')
                    
                    if src and "http" in src:
                        # 1. Filter by Domain (GrabOn/CouponDunia assets)
                        if "grabon" in src or "coupondunia" in src or "gostor" in src:
                            
                            # 2. Filter by Size (Ignore small icons)
                            # We can't check size easily in headless, so we rely on keywords
                            # "upload" usually indicates a user-uploaded banner or logo
                            # "merchant" indicates a brand logo
                            # "banner" indicates a deal banner
                            candidate_urls.append(src)
                            
            except Exception as e:
                print(f"[WARN] Error on {url}: {e}")
                continue
        
        unique_urls = list(set(candidate_urls))
        print(f"[INFO] Mining Complete. Found {len(unique_urls)} unique banners.")
        return unique_urls

    def run(self):
        start = time.time()
        count = 0
        
        driver = self._setup_driver()
        try:
            image_urls = self._collect_image_urls(driver)
        finally:
            driver.quit()

        print(f"[INFO] Downloading {min(len(image_urls), self.total_target)} coupons...")
        pbar = tqdm(total=self.total_target)
        
        for url in image_urls:
            if count >= self.total_target:
                break

            # License Check
            if not is_allowed_source(url):
                continue

            try:
                r = requests.get(url, timeout=8)
                content = r.content
            except:
                continue

            if not validate_image(content):
                continue

            h = file_hash(content)
            if h in self.hashes:
                continue
            self.hashes.add(h)

            filename = f"coupon_{count}.jpg"
            filepath = os.path.join(self.img_path, filename)

            with open(filepath, "wb") as f:
                f.write(content)

            write_metadata(
                self.meta_path,
                [filename, url, time.strftime("%Y-%m-%d %H:%M:%S"), self.category, round(len(content)/1024, 2)]
            )

            count += 1
            pbar.update(1)

        pbar.close()
        end = time.time()
        print(f"\n====== COUPON SCRAPER REPORT ======")
        print(f"Total images: {count}")