"""
test_links.py
Quick sanity-check script to verify the web link finder is working correctly
before running the full pipeline. Mirrors the boarding pass test_links.py.
"""

import logging
from scraper_config import CATEGORY_MAP, SCRAPER_SETTINGS
from utils.web_link_finder import WebLinkFinder

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def main():
    test_category = "retail_coupon"
    test_queries = CATEGORY_MAP[test_category][:2]  # test with first 2 queries only

    logger.info("=" * 60)
    logger.info("  Coupon Pipeline – Link Discovery Test")
    logger.info("=" * 60)
    logger.info(f"Category:  {test_category}")
    logger.info(f"Queries:   {test_queries}")
    logger.info("")

    with WebLinkFinder() as finder:
        urls = finder.discover(test_queries, max_per_query=10)

    logger.info(f"\n✅ Discovered {len(urls)} unique image URLs")
    logger.info("\nSample URLs:")
    for url in urls[:5]:
        logger.info(f"  {url}")

    if len(urls) > 0:
        logger.info("\n✅ Link discovery is working correctly!")
    else:
        logger.warning("\n⚠️  No URLs found – check your Chrome/ChromeDriver setup.")


if __name__ == "__main__":
    main()
