from scrapers.gallery_scraper import GalleryScraper
from scrapers.coupon_scraper import CouponScraper
from scrapers.event_scraper import EventScraper

if __name__ == "__main__":

    # print("Running Gallery...")
    # GalleryScraper().run()

    # print("\nRunning Coupons...")
    # CouponScraper().run()

    print("Running Event Scraper...")
    EventScraper(total_target=500).run()

