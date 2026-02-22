"""
universal_scraper.py
Selenium-based dynamic image scraper for coupon images.
Handles JS-rendered pages, lazy loading, and concurrent downloads.
Mirrors the boarding pass universal_scraper.py.
"""

import os
import time
import random
import logging
import hashlib
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

import requests
from PIL import Image
from io import BytesIO

from scraper_config import SCRAPER_SETTINGS, OUTPUT_SETTINGS
from utils.license_check import should_skip

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.google.com/",
}

_lock = threading.Lock()


def _make_output_dirs(category: str):
    """Ensure all output directories exist for a category."""
    for key in ["raw_dir", "validated_dir", "uncertain_dir", "discarded_dir"]:
        path = Path(OUTPUT_SETTINGS[key]) / category
        path.mkdir(parents=True, exist_ok=True)


def _url_to_filename(url: str, idx: int, category: str) -> str:
    """Generate a stable filename from the URL + index."""
    ext = Path(urlparse(url).path).suffix.lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        ext = ".jpg"
    h = hashlib.md5(url.encode()).hexdigest()[:8]
    return f"{category}_{idx:04d}_{h}{ext}"


def _is_valid_image(content: bytes) -> bool:
    """Check that downloaded bytes are a valid, large-enough image."""
    try:
        img = Image.open(BytesIO(content)).convert("RGB")
        w, h = img.size
        return (
            w >= SCRAPER_SETTINGS["image_min_width"]
            and h >= SCRAPER_SETTINGS["image_min_height"]
        )
    except Exception:
        return False


def _download_one(url: str, dest: Path) -> bool:
    """Download a single image URL to dest. Returns True on success."""
    if dest.exists():
        return True  # already downloaded (resume support)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        content = resp.content
        if _is_valid_image(content):
            dest.write_bytes(content)
            return True
        else:
            logger.debug(f"[Scraper] Skipping small/invalid image: {url}")
            return False
    except Exception as e:
        logger.debug(f"[Scraper] Failed to download {url}: {e}")
        return False


def download_images(
    image_urls: list[str],
    category: str,
    max_count: int | None = None,
) -> list[dict]:
    """
    Download a list of image URLs for a given category.

    Returns:
        list of dicts: [{"path": Path, "url": str}]
    """
    _make_output_dirs(category)
    raw_dir = Path(OUTPUT_SETTINGS["raw_dir"]) / category

    # Filter restricted domains
    filtered = [u for u in image_urls if not should_skip(u)]
    logger.info(
        f"[Scraper] {category}: {len(filtered)}/{len(image_urls)} URLs after license filter"
    )

    if max_count:
        filtered = filtered[:max_count]

    results = []
    counter = {"ok": 0, "fail": 0}

    def _task(idx_url):
        idx, url = idx_url
        filename = _url_to_filename(url, idx, category)
        dest = raw_dir / filename
        ok = _download_one(url, dest)
        with _lock:
            if ok:
                counter["ok"] += 1
                results.append({"path": dest, "url": url})
            else:
                counter["fail"] += 1
        time.sleep(random.uniform(*SCRAPER_SETTINGS["request_delay"]))

    with ThreadPoolExecutor(max_workers=SCRAPER_SETTINGS["download_workers"]) as pool:
        futures = [pool.submit(_task, (i, url)) for i, url in enumerate(filtered)]
        for _ in as_completed(futures):
            pass  # exceptions surfaced via logger inside _task

    logger.info(
        f"[Scraper] {category}: Downloaded {counter['ok']} images "
        f"({counter['fail']} failed)"
    )
    return results
