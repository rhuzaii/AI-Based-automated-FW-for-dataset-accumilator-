"""
utils/license_check.py
Domain-level heuristics to prefer openly licensed coupon image sources
and flag or skip restricted ones. Mirrors the boarding pass license_check.
"""

import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Domains known to have permissive / CC-licensed content
PREFERRED_DOMAINS = [
    "commons.wikimedia.org",
    "flickr.com",
    "unsplash.com",
    "pixabay.com",
    "pexels.com",
    "coupons.com",
    "retailmenot.com",
    "smartsource.com",
    "hopster.com",
    "couponbug.com",
    "couponmom.com",
    "ibotta.com",
]

# Domains that are likely to have restrictive copyright
RESTRICTED_DOMAINS = [
    "gettyimages.com",
    "shutterstock.com",
    "istockphoto.com",
    "alamy.com",
    "corbisimages.com",
]


def get_license_flag(url: str) -> str:
    """
    Returns:
        'preferred'   – known open/permissive domain
        'restricted'  – known rights-managed domain (skip or flag)
        'unknown'     – no special classification
    """
    try:
        domain = urlparse(url).netloc.lower()
    except Exception:
        return "unknown"

    if any(p in domain for p in PREFERRED_DOMAINS):
        return "preferred"
    if any(r in domain for r in RESTRICTED_DOMAINS):
        return "restricted"
    return "unknown"


def should_skip(url: str) -> bool:
    """Return True if this URL should be skipped due to licensing concerns."""
    flag = get_license_flag(url)
    if flag == "restricted":
        logger.debug(f"[LicenseCheck] Skipping restricted domain: {url}")
        return True
    return False
