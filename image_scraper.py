import re
import sys
import time
import urllib.parse
import subprocess
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Auto-install 
def _ensure(pip_name, import_name=None):
    import importlib
    try:
        return importlib.import_module(import_name or pip_name)
    except ImportError:
        print(f"[setup] Installing '{pip_name}' …")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name, "-q"])
        return importlib.import_module(import_name or pip_name)

_ensure("requests")
_ensure("Pillow", "PIL")
_ensure("selenium")
_ensure("webdriver-manager", "webdriver_manager")

from categories import CATEGORIES, list_categories, build_custom
from compliance import compliant_download, filter_urls_by_robots
from utils      import sanitize, ensure_dir, seen_hash_count

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Constants
RAW_FOLDER       = "raw_incoming"
SCROLL_PAUSE     = 1.5
SCROLL_TIMEOUT   = 90
CLICK_PAUSE      = 1.0
MAX_CLICK_TRIES  = 60
DOWNLOAD_WORKERS = 4
MAX_STALL        = 20     

THUMB_SELS = [
    "img.YQ4gaf", "img.rg_i", "img[jsname]",
    ".isv-r img", "g-img img", "[data-ved] img",
]
PANEL_SELS = [
    "img.iPVvYb", "img.r48jcc", "img.sFlh5c",
    "[jsname='figimage'] img", ".tvh9oe img",
    ".p7sI2 img", "img[jsaction]",
]

# Thread-safe status line 
_print_lock  = threading.Lock()
_status_text = ""

def _status(msg: str):
    global _status_text
    _status_text = msg
    sys.stdout.write(f"\r   {msg:<78}")
    sys.stdout.flush()

def _clear_status():
    global _status_text
    _status_text = ""
    sys.stdout.write(f"\r{' ' * 82}\r")
    sys.stdout.flush()

def tprint(*args, **kwargs):
    with _print_lock:
        sys.stdout.write(f"\r{' ' * 82}\r")
        print(*args, **kwargs)
        if _status_text:
            sys.stdout.write(f"   {_status_text:<78}")
            sys.stdout.flush()

# Selenium driver 
def build_driver() -> webdriver.Chrome:
    from utils import random_ua
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1280,900")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_argument(f"user-agent={random_ua()}")
    service = Service(ChromeDriverManager().install())
    driver  = webdriver.Chrome(service=service, options=opts)
    driver.execute_script(
        "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"
    )
    return driver

# URL extraction 
def _urls_from_source(source: str) -> list:
    found = []
    for u in re.findall(r'"(https?://[^"]{10,}\.(?:jpg|jpeg|png|webp)(?:[^"]{0,200}))"', source):
        u = u.replace("\\u003d", "=").replace("\\u0026", "&")
        if "gstatic" not in u and "google" not in u:
            found.append(u)
    for u in re.findall(r'(?:data-src|src)="(https?://[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"', source):
        if "gstatic" not in u and "google" not in u:
            found.append(u)
    return list(dict.fromkeys(found))


def collect_urls(driver: webdriver.Chrome, keyword: str, needed: int) -> list:
    encoded  = urllib.parse.quote(keyword)
    page_url = f"https://www.google.com/search?tbm=isch&q={encoded}&tbs=il:cl&hl=en"

    _status(f"Opening Google: {keyword[:50]}")
    driver.get(page_url)
    time.sleep(2.5)

    for xp in ['//button[contains(.,"Accept all")]', '//button[contains(.,"Accept")]',
               '//button[contains(.,"I agree")]', '//button[contains(.,"Agree")]']:
        try:
            driver.find_element(By.XPATH, xp).click()
            time.sleep(0.8)
            break
        except Exception:
            pass

    all_urls  = []
    deadline  = time.time() + SCROLL_TIMEOUT
    prev_h    = 0
    no_change = 0
    scroll_n  = 0

    # Phase 1 — scroll + JSON extraction
    while time.time() < deadline:
        if len(all_urls) >= needed * 2:
            break
        scroll_n += 1
        secs_left = int(deadline - time.time())
        _status(f"[scroll {scroll_n}] {len(all_urls)} URLs | {secs_left}s | {keyword[:35]}")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(SCROLL_PAUSE)
        try:
            btn = driver.find_element(By.CSS_SELECTOR, "input.mye4qd, button.mye4qd")
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(1.2)
        except Exception:
            pass
        all_urls.extend(_urls_from_source(driver.page_source))
        all_urls = list(dict.fromkeys(all_urls))
        cur_h = driver.execute_script("return document.body.scrollHeight")
        if cur_h == prev_h:
            no_change += 1
            if no_change >= 3:
                break
        else:
            no_change = 0
        prev_h = cur_h

    tprint(f"      [1/3] {scroll_n} scrolls → {len(all_urls)} URLs")

    # Phase 2 — click thumbnails
    if len(all_urls) < needed:
        thumbs = []
        for sel in THUMB_SELS:
            try:
                found = driver.find_elements(By.CSS_SELECTOR, sel)
                if found:
                    thumbs = found
                    break
            except Exception:
                pass
        clicks = 0
        for thumb in thumbs[:MAX_CLICK_TRIES]:
            if len(all_urls) >= needed * 2 or clicks >= MAX_CLICK_TRIES:
                break
            _status(f"[click {clicks+1}/{min(len(thumbs),MAX_CLICK_TRIES)}] {len(all_urls)} URLs | {keyword[:35]}")
            try:
                driver.execute_script("arguments[0].scrollIntoView(true);", thumb)
                driver.execute_script("arguments[0].click();", thumb)
                time.sleep(CLICK_PAUSE)
                for psel in PANEL_SELS:
                    for p in driver.find_elements(By.CSS_SELECTOR, psel):
                        src = p.get_attribute("src") or p.get_attribute("data-src") or ""
                        if (src.startswith("http") and "base64" not in src
                                and "gstatic" not in src and "google" not in src
                                and len(src) > 30):
                            all_urls.append(src)
                clicks += 1
            except Exception:
                pass
        tprint(f"      [2/3] {clicks} clicks → {len(set(all_urls))} URLs")

    # Phase 3 — img tag scan
    if len(all_urls) < needed:
        _status(f"[3/3] img tag scan | {keyword[:45]}")
        for img in driver.find_elements(By.TAG_NAME, "img"):
            for attr in ["src", "data-src", "data-iurl"]:
                val = img.get_attribute(attr) or ""
                if (val.startswith("http") and "base64" not in val
                        and "gstatic" not in val and "google" not in val
                        and any(val.lower().endswith(e) for e in [".jpg",".jpeg",".png",".webp"])):
                    all_urls.append(val)
        tprint(f"      [3/3] img scan → {len(set(all_urls))} URLs")

    return list(dict.fromkeys(all_urls))


#  Download batch 
def download_batch(urls: list, count: int, raw_dir: Path,
                   cat_slug: str, kw_idx: int, start_num: int) -> int:
    saved        = 0
    consec_fails = 0
    lock         = threading.Lock()

    tasks = [
        (url, str(raw_dir / f"{cat_slug}_kw{kw_idx}_{start_num+i+1:04d}"))
        for i, url in enumerate(urls)
    ]

    def _dl(args):
        url, stem = args
        return compliant_download(url, stem), stem

    _status(f"Downloading 0/{len(tasks)} | kw{kw_idx}")

    with ThreadPoolExecutor(max_workers=DOWNLOAD_WORKERS) as pool:
        futures = {pool.submit(_dl, t): t for t in tasks}
        for future in as_completed(futures):
            with lock:
                stop = saved >= count or consec_fails >= MAX_STALL
            if stop:
                future.cancel()
                continue
            try:
                ok, stem = future.result()
                with lock:
                    if ok and saved < count:
                        saved += 1
                        consec_fails = 0
                        n = start_num + saved
                        _status(f"Downloading {saved}/{len(tasks)} | kw{kw_idx}")
                        tprint(f"       [{n}] {Path(stem).name}")
                    elif not ok:
                        consec_fails += 1
                        if consec_fails >= MAX_STALL:
                            tprint(f"       {MAX_STALL} consecutive failures — advancing to next keyword")
            except Exception:
                with lock:
                    consec_fails += 1

    _clear_status()
    return saved


# Per-keyword runner 
def run_keyword(driver, keyword, count, raw_dir, cat_slug, kw_idx, start_num) -> int:
    tprint(f"\n     Keyword [{kw_idx}]: '{keyword}'")

    # Step 1: collect raw URLs from Google
    raw_urls = collect_urls(driver, keyword, count)
    if not raw_urls:
        tprint("        No URLs found — skipping.")
        return 0

    tprint(f"       {len(raw_urls)} raw URLs collected")

    # Step 2: pre-filter by robots.txt 
    _status(f"Checking robots.txt for {len(raw_urls)} URLs …")
    allowed_urls = filter_urls_by_robots(raw_urls, print_fn=tprint)
    tprint(f"       {len(allowed_urls)}/{len(raw_urls)} URLs passed robots.txt")

    if not allowed_urls:
        tprint("      (warning)  All URLs blocked by robots.txt — skipping keyword.")
        return 0

    # Step 3: download in parallel (no robots blocking inside workers)
    return download_batch(allowed_urls, count, raw_dir, cat_slug, kw_idx, start_num)


def scrape_category(cat: dict, count: int, base_dir: Path):
    name     = cat["name"]
    keywords = cat["keywords"]
    cat_slug = sanitize(name)
    raw_dir  = ensure_dir(base_dir / RAW_FOLDER)

    print(f"\n{'='*64}")
    print(f"  Category  : {name}  [{cat_slug}]")
    print(f"  Target    : {count} images")
    print(f"  Keywords  : {len(keywords)}")
    print(f"  Output    : {raw_dir}")
    print(f"  Threads   : {DOWNLOAD_WORKERS} | Stall: {MAX_STALL} | robots: pre-filtered")
    print(f"{'='*64}")

    _status("Launching headless Chrome …")
    driver = build_driver()
    _clear_status()

    total = 0
    try:
        for idx, kw in enumerate(keywords, start=1):
            if total >= count:
                break
            got   = run_keyword(driver, kw, count - total, raw_dir, cat_slug, idx, total)
            total += got
            print(f"\n    ── kw{idx}/{len(keywords)}: +{got}"
                  f" | total {total}/{count}"
                  f" | hashes {seen_hash_count()} ──")
            if total < count and idx < len(keywords):
                time.sleep(1.5)
    finally:
        driver.quit()

    real = len(list(raw_dir.glob(f"{cat_slug}_*")))
    print(f"\n   {real} '{name}' images in raw_incoming/")
    if total < count:
        print(f"    {total}/{count} — Google CC filter limits results per query.")


def interactive_mode():
    print("      License-Free Image Scraper  (Google Images + CC filter)")
    list_categories()

    raw = input("Select category number (example: 1,3 or 'all'): ").strip()
    selected = []
    if raw.lower() == "all":
        selected = list(CATEGORIES.values())
    else:
        for token in [t.strip() for t in raw.split(",")]:
            if token in CATEGORIES:
                selected.append(CATEGORIES[token])
            elif token == "7":
                cname = input("  Custom category name : ").strip()
                ckw   = input("  Search keyword       : ").strip()
                if cname and ckw:
                    selected.append(build_custom(cname, ckw))

    if not selected:
        print("[!] No valid selection. Exiting.")
        sys.exit(1)

    count_raw = input("\nHow many images per category? (default 10) ").strip()
    count     = int(count_raw) if count_raw.isdigit() and int(count_raw) > 0 else 10

    out_raw  = input("Output directory [default: ./scraped_images]: ").strip()
    base_dir = Path(out_raw if out_raw else "./scraped_images")

    print(f"\n {len(selected)} categories × {count} images")
    print(f"    {(base_dir / RAW_FOLDER).resolve()}")
    print(f"    {DOWNLOAD_WORKERS} download threads | robots pre-filtered\n")

    for cat in selected:
        scrape_category(cat, count, base_dir)

    print(f"\n\n All done!")
    print(f"    {(base_dir / RAW_FOLDER).resolve()}")
    print(f"    Unique images: {seen_hash_count()}\n")


def cli_mode():
    import argparse
    parser = argparse.ArgumentParser(description="License-Free Google Image Scraper")
    parser.add_argument("-c", "--category", nargs="+")
    parser.add_argument("-n", "--count", type=int, default=10)
    parser.add_argument("-o", "--output", default="./scraped_images")
    args = parser.parse_args()

    matched = []
    if args.category:
        for ui in args.category:
            for cat in CATEGORIES.values():
                if ui.lower() in cat["name"].lower():
                    matched.append(cat)
                    break
    if not matched:
        interactive_mode()
        return

    base_dir = Path(args.output)
    for cat in matched:
        scrape_category(cat, args.count, base_dir)
    print(f"\n🎉 Done! → {(base_dir / RAW_FOLDER).resolve()}\n")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cli_mode()
    else:
        interactive_mode()