"""
ai_pipeline_manager.py
Main orchestrator for the Coupon Dataset Accumulation Pipeline.

Pipeline stages:
  1. Webpage Discovery    – find image URLs via Google/Bing Image Search
  2. Image Scraping       – download images with Selenium + requests
  3. Duplicate Detection  – perceptual hash dedup
  4. AI Validation        – CLIP-based coupon relevance scoring
  5. Dataset Categorization – move images into validated / uncertain / discarded

Mirrors the boarding pass ai_pipeline_manager.py, adapted for coupons.

Usage:
    python ai_pipeline_manager.py
"""

import logging
import shutil
import time
from datetime import datetime
from pathlib import Path

from scraper_config import CATEGORY_MAP, SCRAPER_SETTINGS, OUTPUT_SETTINGS
from universal_scraper import download_images
from utils.web_link_finder import WebLinkFinder
from utils.ai_classifier import CouponCLIPClassifier
from utils.hasher import DuplicateDetector
from utils.metadata import MetadataTracker

# ─────────────────────────────────────────────
#  Logging setup
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("pipeline.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────
def _ensure_dirs():
    for key in ["raw_dir", "validated_dir", "uncertain_dir", "discarded_dir"]:
        Path(OUTPUT_SETTINGS[key]).mkdir(parents=True, exist_ok=True)


def _move_image(src: Path, result: str, category: str) -> Path:
    """Move an image to the appropriate output directory."""
    dest_dir = Path(OUTPUT_SETTINGS[f"{result}_dir"]) / category
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    shutil.move(str(src), str(dest))
    return dest


def _write_report(stats: dict, elapsed: float):
    report_path = Path(OUTPUT_SETTINGS["report_file"])
    report_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "=" * 55,
        "  COUPON DATASET PIPELINE REPORT",
        f"  Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"  Total runtime: {elapsed:.1f}s",
        "=" * 55,
        "",
    ]

    grand = {"discovered": 0, "downloaded": 0, "duplicates": 0,
             "validated": 0, "uncertain": 0, "discarded": 0}

    for category, s in stats.items():
        lines.append(f"Category: {category}")
        lines.append(f"  URLs discovered:  {s['discovered']}")
        lines.append(f"  Images downloaded:{s['downloaded']}")
        lines.append(f"  Duplicates removed:{s['duplicates']}")
        lines.append(f"  ✅ Validated:      {s['validated']}")
        lines.append(f"  ❓ Uncertain:      {s['uncertain']}")
        lines.append(f"  ❌ Discarded:      {s['discarded']}")
        lines.append("")
        for k in grand:
            grand[k] += s.get(k, 0)

    lines += [
        "─" * 55,
        "TOTALS",
        f"  URLs discovered:  {grand['discovered']}",
        f"  Images downloaded:{grand['downloaded']}",
        f"  Duplicates removed:{grand['duplicates']}",
        f"  ✅ Validated:      {grand['validated']}",
        f"  ❓ Uncertain:      {grand['uncertain']}",
        f"  ❌ Discarded:      {grand['discarded']}",
        "=" * 55,
    ]

    report_text = "\n".join(lines)
    report_path.write_text(report_text, encoding="utf-8")
    print("\n" + report_text)
    logger.info(f"Report saved → {report_path}")


# ─────────────────────────────────────────────
#  Pipeline
# ─────────────────────────────────────────────
def run_pipeline():
    logger.info("╔══════════════════════════════════════════════╗")
    logger.info("║   AI Coupon Dataset Accumulation Pipeline    ║")
    logger.info("╚══════════════════════════════════════════════╝")

    _ensure_dirs()
    start_time = time.time()

    # Initialise shared components
    classifier = CouponCLIPClassifier()
    metadata = MetadataTracker()
    stats: dict[str, dict] = {}

    for category, queries in CATEGORY_MAP.items():
        logger.info(f"\n{'─'*50}")
        logger.info(f"STAGE 1/4 – Webpage Discovery  [{category}]")
        logger.info(f"{'─'*50}")

        with WebLinkFinder() as finder:
            all_urls = finder.discover(
                queries,
                max_per_query=SCRAPER_SETTINGS["max_images_per_query"],
            )

        logger.info(f"Discovered {len(all_urls)} image URLs for [{category}]")

        # ── STAGE 2: Download ──────────────────────────────────────────
        logger.info(f"\nSTAGE 2/4 – Image Scraping    [{category}]")
        downloaded = download_images(
            all_urls,
            category=category,
            max_count=SCRAPER_SETTINGS["max_images_per_category"],
        )
        logger.info(f"Downloaded {len(downloaded)} images for [{category}]")

        # ── STAGE 3: Duplicate detection ──────────────────────────────
        logger.info(f"\nSTAGE 3/4 – Duplicate Detection [{category}]")
        hasher = DuplicateDetector(threshold=5)
        unique_downloaded = []
        dup_count = 0
        for item in downloaded:
            if hasher.is_duplicate(item["path"]):
                item["path"].unlink(missing_ok=True)
                dup_count += 1
                metadata.add(
                    item["path"].name, item["url"], category, 0.0, "duplicate"
                )
            else:
                unique_downloaded.append(item)

        logger.info(
            f"Kept {len(unique_downloaded)} unique images "
            f"({dup_count} duplicates removed)"
        )

        # ── STAGE 4: AI Validation ─────────────────────────────────────
        logger.info(f"\nSTAGE 4/4 – CLIP Validation   [{category}]")
        cat_stats = {
            "discovered": len(all_urls),
            "downloaded": len(downloaded),
            "duplicates": dup_count,
            "validated": 0,
            "uncertain": 0,
            "discarded": 0,
        }

        paths = [item["path"] for item in unique_downloaded]
        url_map = {item["path"]: item["url"] for item in unique_downloaded}

        classification_results = classifier.classify_batch(paths)

        for path, result, score in classification_results:
            dest = _move_image(path, result, category)
            cat_stats[result] += 1
            metadata.add(dest.name, url_map.get(path, ""), category, score, result)

        logger.info(
            f"[{category}] ✅ Validated: {cat_stats['validated']}  "
            f"❓ Uncertain: {cat_stats['uncertain']}  "
            f"❌ Discarded: {cat_stats['discarded']}"
        )
        stats[category] = cat_stats

    # ── Final report ───────────────────────────────────────────────────
    metadata.save()
    elapsed = time.time() - start_time
    _write_report(stats, elapsed)


if __name__ == "__main__":
    run_pipeline()
