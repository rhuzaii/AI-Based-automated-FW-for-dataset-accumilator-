import os
import time
import requests
from tqdm import tqdm
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager


class UniversalScraper:
    def __init__(self, source_urls, download_dir):
        self.source_urls = source_urls
        self.download_dir = download_dir   # ✅ unified name
        os.makedirs(self.download_dir, exist_ok=True)

    # --------------------------------------------------
    # Selenium Driver Setup
    # --------------------------------------------------
    def _setup_driver(self):
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--window-size=1920,1080")

        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        # Anti-bot tweaks
        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        return driver

    # --------------------------------------------------
    # Collect Image URLs
    # --------------------------------------------------
    def _collect_image_urls(self, driver, total_target):
        candidate_urls = []
        buffer_limit = int(total_target * 1.2)

        for start_url in self.source_urls:
            if len(candidate_urls) >= buffer_limit:
                break

            current_url = start_url
            page_num = 1
            max_pages = 15

            while page_num <= max_pages:
                if len(candidate_urls) >= buffer_limit:
                    break

                try:
                    driver.get(current_url)
                    time.sleep(3)

                    for _ in range(3):
                        driver.execute_script(
                            "window.scrollTo(0, document.body.scrollHeight);"
                        )
                        time.sleep(1.5)

                    images = driver.find_elements(By.TAG_NAME, "img")
                    page_count = 0

                    for img in images:
                        src = img.get_attribute("data-src") or img.get_attribute("src")
                        if not src or not src.startswith("http"):
                            continue

                        if any(x in src.lower() for x in ["logo", "icon", "avatar"]):
                            continue

                        if src not in candidate_urls:
                            candidate_urls.append(src)
                            page_count += 1

                    print(
                        f"      -> Page {page_num}: Found {page_count} new images. "
                        f"(Total: {len(candidate_urls)}/{buffer_limit})"
                    )

                    if page_count == 0:
                        print("      [WARN] No images found. Moving to next site.")
                        break

                    # Pagination (best-effort)
                    page_num += 1
                    current_url = f"{start_url}/{page_num}"

                except Exception as e:
                    print(f"      [WARN] Page error: {e}")
                    break

        unique_urls = list(set(candidate_urls))
        print(f"\n Found {len(unique_urls)} images.")
        return unique_urls

    # --------------------------------------------------
    # Download Images
    # --------------------------------------------------
    def _download_images(self, image_urls, limit):
        downloaded = 0
        pbar = tqdm(total=min(len(image_urls), limit))

        for url in image_urls:
            if downloaded >= limit:
                break

            try:
                r = requests.get(url, timeout=10, stream=True)
                if r.status_code != 200:
                    continue

                ext = url.split("?")[0].split(".")[-1].lower()
                if ext not in ["jpg", "jpeg", "png", "webp"]:
                    ext = "jpg"

                filename = f"img_{int(time.time()*1000)}_{downloaded}.{ext}"
                path = os.path.join(self.download_dir, filename)

                with open(path, "wb") as f:
                    for chunk in r.iter_content(1024):
                        f.write(chunk)

                downloaded += 1
                pbar.update(1)

            except Exception:
                continue

        pbar.close()
        print(f"[DONE] Downloaded {downloaded} Raw Images.")

    # --------------------------------------------------
    # Public Runner
    # --------------------------------------------------
    def run(self, total_target=300):
        print("--- STARTING UNIVERSAL SCRAPER (AUTO LINK MODE) ---")

        driver = self._setup_driver()
        try:
            image_urls = self._collect_image_urls(driver, total_target)
        finally:
            driver.quit()

        self._download_images(image_urls, total_target)