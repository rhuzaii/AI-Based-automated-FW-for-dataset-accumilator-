import socket
import urllib.robotparser
from pathlib import Path
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

import requests

from utils import (
    is_duplicate,
    is_valid_image,
    convert_to_jpg,
    ext_from_content_type,
    random_ua,
)

#  Config 
SCRAPER_UA       = "LicensedImageScraper/1.0"
DOWNLOAD_TIMEOUT = 8
ROBOTS_TIMEOUT   = 4
ROBOTS_WORKERS   = 10

# robots.txt cache 
_robots_cache:   dict = {}
_robots_printed: set  = set()
_cache_lock = threading.Lock()


def _fetch_robots(domain: str):
    with _cache_lock:
        if domain in _robots_cache:
            return _robots_cache[domain]

    result = None
    old_timeout = socket.getdefaulttimeout()
    try:
        socket.setdefaulttimeout(ROBOTS_TIMEOUT)
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(f"https://{domain}/robots.txt")
        rp.read()
        result = rp
    except Exception:
        result = None
    finally:
        socket.setdefaulttimeout(old_timeout)

    with _cache_lock:
        _robots_cache[domain] = result
    return result


def _is_allowed(url: str) -> bool:
    try:
        domain = urlparse(url).netloc
        rp = _fetch_robots(domain)
        if rp is None:
            return True
        return rp.can_fetch(SCRAPER_UA, url)
    except Exception:
        return True


def filter_urls_by_robots(urls: list, print_fn=print) -> list:
    if not urls:
        return []

    domains = list({urlparse(u).netloc for u in urls})

    with ThreadPoolExecutor(max_workers=ROBOTS_WORKERS) as pool:
        futures = {pool.submit(_fetch_robots, d): d for d in domains}
        for f in as_completed(futures):
            domain = futures[f]
            if domain not in _robots_printed:
                _robots_printed.add(domain)
                try:
                    rp = f.result()
                    if rp is not None:
                        allowed = rp.can_fetch(SCRAPER_UA, f"https://{domain}/")
                        tag = "✔" if allowed else "✗ blocked"
                        print_fn(f"      [robots] {tag}: {domain}")
                except Exception:
                    pass

    allowed = [u for u in urls if _is_allowed(u)]
    blocked = len(urls) - len(allowed)
    if blocked:
        print_fn(f"      [robots] {blocked}/{len(urls)} blocked → {len(allowed)} allowed")
    return allowed


def clear_robots_cache():
    with _cache_lock:
        _robots_cache.clear()
        _robots_printed.clear()


#  Pure downloader (robots already pre-filtered) 
def compliant_download(url: str, dest_stem: str) -> bool:
    try:
        headers = {
            "User-Agent": random_ua(),
            "Referer":    "https://www.google.com/",
            "Accept":     "image/webp,image/apng,image/*,*/*;q=0.8",
        }
        r = requests.get(url, headers=headers, timeout=DOWNLOAD_TIMEOUT, stream=True)
        if r.status_code != 200:
            return False
        content = r.content
    except Exception:
        return False

    if is_duplicate(content):
        return False

    try:
        ct    = r.headers.get("Content-Type", "image/jpeg")
        ext   = ext_from_content_type(ct)
        final = Path(dest_stem + ext)
        with open(final, "wb") as fh:
            fh.write(content)
        if not is_valid_image(final):
            final.unlink(missing_ok=True)
            return False
        convert_to_jpg(final)
        return True
    except Exception:
        try:
            Path(dest_stem + ".jpg").unlink(missing_ok=True)
        except Exception:
            pass
        return False