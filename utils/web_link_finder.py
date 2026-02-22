"""
utils/web_link_finder.py
Discovers image-rich webpages containing coupon images using Selenium.
Mirrors the boarding pass web_link_finder but with coupon-specific logic.
"""

import time
import random
import logging
from urllib.parse import urlparse, quote_plus

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from scraper_config import SEARCH_CONFIG, SCRAPER_SETTINGS, BLOCKED_DOMAINS

logger = logging.getLogger(__name__)


def _build_driver(headless: bool = True) -> webdriver.Chrome:
    """Create a stealth-ish Chrome WebDriver instance."""
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    driver = webdriver.Chrome(options=options)
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return driver


def _is_blocked_domain(url: str) -> bool:
    try:
        domain = urlparse(url).netloc.lower()
        return any(bd in domain for bd in BLOCKED_DOMAINS)
    except Exception:
        return False


def _scroll_page(driver, count: int = 3):
    """Scroll to load lazy content."""
    for _ in range(count):
        driver.execute_script("window.scrollBy(0, window.innerHeight * 1.5);")
        time.sleep(random.uniform(0.5, 1.2))


def find_image_urls_google(query: str, driver: webdriver.Chrome) -> list[str]:
    """
    Search Google Images for a query and return src URLs of found images.
    """
    encoded = quote_plus(query)
    url = SEARCH_CONFIG["google_images_url"].format(query=encoded)
    image_urls = []

    try:
        driver.get(url)
        WebDriverWait(driver, SCRAPER_SETTINGS["page_load_timeout"]).until(
            EC.presence_of_element_located((By.TAG_NAME, "img"))
        )
        _scroll_page(driver, SCRAPER_SETTINGS["scroll_count"])

        img_elements = driver.find_elements(By.CSS_SELECTOR, "img[src]")
        for el in img_elements:
            src = el.get_attribute("src") or ""
            data_src = el.get_attribute("data-src") or ""
            for candidate in [src, data_src]:
                if candidate.startswith("http") and not _is_blocked_domain(candidate):
                    image_urls.append(candidate)

        # Also try to get full-res URLs from result anchors
        anchors = driver.find_elements(By.CSS_SELECTOR, "a[href*='imgurl=']")
        for a in anchors:
            href = a.get_attribute("href") or ""
            if "imgurl=" in href:
                img_url = href.split("imgurl=")[1].split("&")[0]
                if img_url.startswith("http") and not _is_blocked_domain(img_url):
                    image_urls.append(img_url)

    except TimeoutException:
        logger.warning(f"Timeout loading Google Images for query: {query}")
    except WebDriverException as e:
        logger.error(f"WebDriver error: {e}")

    return list(dict.fromkeys(image_urls))  # deduplicate, preserve order


def find_image_urls_bing(query: str, driver: webdriver.Chrome) -> list[str]:
    """
    Search Bing Images for a query and return image URLs.
    """
    encoded = quote_plus(query)
    url = SEARCH_CONFIG["bing_images_url"].format(query=encoded)
    image_urls = []

    try:
        driver.get(url)
        WebDriverWait(driver, SCRAPER_SETTINGS["page_load_timeout"]).until(
            EC.presence_of_element_located((By.CLASS_NAME, "iusc"))
        )
        _scroll_page(driver, SCRAPER_SETTINGS["scroll_count"])

        # Bing stores full URLs in data-m attribute JSON
        import json
        items = driver.find_elements(By.CLASS_NAME, "iusc")
        for item in items:
            data_m = item.get_attribute("data-m") or "{}"
            try:
                meta = json.loads(data_m)
                murl = meta.get("murl", "")
                if murl.startswith("http") and not _is_blocked_domain(murl):
                    image_urls.append(murl)
            except json.JSONDecodeError:
                pass

    except TimeoutException:
        logger.warning(f"Timeout loading Bing Images for query: {query}")
    except WebDriverException as e:
        logger.error(f"WebDriver error: {e}")

    return list(dict.fromkeys(image_urls))


class WebLinkFinder:
    """
    Orchestrates webpage/image URL discovery across all coupon categories.
    """

    def __init__(self):
        self.headless = SCRAPER_SETTINGS["headless"]
        self.engine = SEARCH_CONFIG["use_engine"]
        self.driver = None

    def __enter__(self):
        self.driver = _build_driver(self.headless)
        return self

    def __exit__(self, *args):
        if self.driver:
            self.driver.quit()

    def discover(self, queries: list[str], max_per_query: int = 40) -> list[str]:
        """
        Given a list of search queries, return a deduplicated list of image URLs.
        """
        all_urls = []
        for query in queries:
            logger.info(f"[WebLinkFinder] Searching: '{query}'")
            if self.engine == "bing":
                urls = find_image_urls_bing(query, self.driver)
            else:
                urls = find_image_urls_google(query, self.driver)

            urls = urls[:max_per_query]
            all_urls.extend(urls)
            logger.info(f"  → Found {len(urls)} URLs")
            time.sleep(random.uniform(*SCRAPER_SETTINGS["request_delay"]))

        return list(dict.fromkeys(all_urls))
