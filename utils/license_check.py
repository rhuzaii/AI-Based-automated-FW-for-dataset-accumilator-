from urllib.parse import urlparse
import urllib.robotparser

# -------------------------
# Allowed domains (license safe)
# -------------------------
ALLOWED_DOMAINS = [
    # gallery
    "picsum.photos",
    "loremflickr.com",

    # events
    "www.greetingsisland.com",
    "greetingsisland.com",
    "gi-cdn.s3.amazonaws.com",
    "cdn.greetingsisland.com",
    "images.greetingsisland.com",
    "d1csarkz8obe9u.cloudfront.net",

    # coupons (NEW)
    "www.grabon.in",
    "grabon.in",
    "assets.grabon.in",          # GrabOn Images
    "www.coupondunia.in",
    "coupondunia.in",
    "cdn.coupondunia.in",        # CouponDunia Images
    "img.gostor.com",            # Common CDN
    "images.freekaamaal.com"     # FreeKaaMaal Images
]

def is_allowed_source(url):
    try:
        domain = urlparse(url).netloc
        for allowed in ALLOWED_DOMAINS:
            if domain == allowed or domain.endswith("." + allowed):
                return True
        return False
    except:
        return False

# -------------------------
# robots.txt check
# -------------------------
def allowed_by_robots(url):
    try:
        rp = urllib.robotparser.RobotFileParser()
        base = "/".join(url.split("/")[:3])
        rp.set_url(base + "/robots.txt")
        rp.read()
        return rp.can_fetch("*", url)
    except:
        return True