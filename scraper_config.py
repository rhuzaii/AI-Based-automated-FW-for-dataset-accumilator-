"""
scraper_config.py - Configuration for Coupon Dataset Accumulation Pipeline
Mirrors the boarding pass pipeline structure but adapted for coupon images.
"""

# ─────────────────────────────────────────────
#  CATEGORY MAP  (category → search queries)
# ─────────────────────────────────────────────
CATEGORY_MAP = {
    "retail_coupon": [
        "retail store coupon image",
        "supermarket discount coupon photo",
        "grocery store coupon sample",
        "printed retail coupon example",
        "store coupon barcode image",
    ],
    "digital_coupon": [
        "digital coupon screenshot",
        "online promo code coupon",
        "app coupon discount image",
        "mobile coupon barcode scan",
        "e-coupon digital example",
    ],
    "restaurant_coupon": [
        "restaurant coupon image",
        "fast food discount coupon photo",
        "food delivery coupon example",
        "pizza coupon printable image",
        "dining coupon sample photo",
    ],
    "manufacturer_coupon": [
        "manufacturer coupon sample image",
        "brand product coupon photo",
        "CPG coupon barcode example",
        "manufacturer discount coupon real",
        "FMCG coupon template image",
    ],
    "gift_card_voucher": [
        "gift card voucher image",
        "store gift voucher photo",
        "discount voucher coupon example",
        "cashback voucher image sample",
        "prepaid gift card coupon photo",
    ],
}

# ─────────────────────────────────────────────
#  SCRAPER SETTINGS
# ─────────────────────────────────────────────
SCRAPER_SETTINGS = {
    "max_images_per_query": 40,       # images to attempt per search query
    "max_images_per_category": 300,   # hard cap per category
    "scroll_count": 5,                # page scrolls to load lazy images
    "page_load_timeout": 20,          # seconds
    "headless": True,                 # run Chrome without UI
    "image_min_width": 100,           # px – skip thumbnails
    "image_min_height": 100,
    "download_workers": 6,            # parallel download threads
    "request_delay": (0.5, 1.5),      # random delay range between requests (sec)
}

# ─────────────────────────────────────────────
#  CLIP VALIDATION SETTINGS
# ─────────────────────────────────────────────
CLIP_SETTINGS = {
    "model_name": "openai/clip-vit-base-patch32",
    "confidence_threshold": 0.25,     # min cosine similarity to keep image
    "uncertain_threshold": 0.20,      # below this → discard; between → uncertain
    "batch_size": 32,
    # Text prompts used for CLIP similarity scoring (positive + negative)
    "positive_prompts": [
        "a coupon with a discount offer",
        "a store coupon with barcode",
        "a promotional coupon clipping",
        "a digital coupon with promo code",
        "a paper coupon with expiry date",
    ],
    "negative_prompts": [
        "a random photograph",
        "a person smiling",
        "a landscape or scenery",
        "a logo or icon",
        "a blank white page",
    ],
}

# ─────────────────────────────────────────────
#  OUTPUT PATHS
# ─────────────────────────────────────────────
OUTPUT_SETTINGS = {
    "raw_dir": "datasets/raw",
    "validated_dir": "datasets/validated",
    "uncertain_dir": "datasets/uncertain",
    "discarded_dir": "datasets/discarded",
    "metadata_file": "datasets/metadata.json",
    "report_file": "datasets/pipeline_report.txt",
}

# ─────────────────────────────────────────────
#  SEARCH ENGINE URLS
# ─────────────────────────────────────────────
SEARCH_CONFIG = {
    "google_images_url": "https://www.google.com/search?tbm=isch&q={query}",
    "bing_images_url": "https://www.bing.com/images/search?q={query}",
    "use_engine": "google",           # "google" or "bing"
}

# ─────────────────────────────────────────────
#  BLOCKED DOMAINS  (known non-coupon heavy sites)
# ─────────────────────────────────────────────
BLOCKED_DOMAINS = [
    "pinterest.com",
    "instagram.com",
    "tiktok.com",
    "facebook.com",
    "twitter.com",
    "x.com",
]
