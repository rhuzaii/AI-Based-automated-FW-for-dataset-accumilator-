from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import random
from urllib.parse import urlparse, parse_qs, unquote


def _unwrap_duckduckgo_url(url):
    """
    Extract real destination from DuckDuckGo redirect URLs
    """
    parsed = urlparse(url)
    if "duckduckgo.com/l/" in url:
        qs = parse_qs(parsed.query)
        if "uddg" in qs:
            return unquote(qs["uddg"][0])
    return url


def find_links(search_query, max_links=20):
    print(f"[LINK-FINDER] Searching for: {search_query}")

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")

    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    search_url = (
        "https://duckduckgo.com/html/?q="
        + search_query.replace(" ", "+")
    )

    driver.get(search_url)
    time.sleep(random.uniform(2.5, 4))

    links = set()
    results = driver.find_elements(By.CSS_SELECTOR, "a.result__a")

    for r in results:
        href = r.get_attribute("href")
        if not href:
            continue

        real_url = _unwrap_duckduckgo_url(href)

        if real_url.startswith("http"):
            links.add(real_url)

        if len(links) >= max_links:
            break

    driver.quit()

    print(f"[LINK-FINDER] Found {len(links)} links")
    return list(links)