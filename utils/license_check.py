from urllib.parse import urlparse
import urllib.robotparser


# Allowed domains 
ALLOWED_DOMAINS = [
    # Gallery Category
    "unsplash.com",
    "images.unsplash.com",
    "plus.unsplash.com",
    "www.pexels.com",
    "pexels.com",
    "images.pexels.com",
    "picsum.photos",
    "loremflickr.com",

    # Events
    "www.greetingsisland.com",
    "greetingsisland.com",
    "gi-cdn.s3.amazonaws.com",
    "cdn.greetingsisland.com",
    "images.greetingsisland.com",
    "d1csarkz8obe9u.cloudfront.net",

    # Coupons
    "www.grabon.in",
    "grabon.in",
    "assets.grabon.in",
    "www.coupondunia.in",
    "coupondunia.in",
    "cdn.coupondunia.in",
    "img.gostor.com",
    "images.freekaamaal.com",

    # Boarding Passes
    "www.freepik.com",
    "freepik.com",
    "img.freepik.com"  
]

def is_allowed_source(url):
    try:
        domain = urlparse(url).netloc
        # Check against whitelist
        for allowed in ALLOWED_DOMAINS:
            if domain == allowed or domain.endswith("." + allowed):
                return True
        return False
    except:
        return False


# robots.txt check
def allowed_by_robots(url):
    try:
        rp = urllib.robotparser.RobotFileParser()
        base = "/".join(url.split("/")[:3])
        rp.set_url(base + "/robots.txt")
        rp.read()
        return rp.can_fetch("*", url)
    except:
        return True