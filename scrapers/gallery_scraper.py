import os
import time
import requests
import shutil
from tqdm import tqdm

from utils.validator import validate_image
from utils.metadata import write_metadata
from utils.hasher import file_hash
from utils.license_check import is_allowed_source, allowed_by_robots


class GalleryScraper:

    def __init__(self):
        self.category = "gallery"

        self.base_path = f"datasets/{self.category}"
        self.img_path = f"{self.base_path}/images"
        self.meta_path = f"{self.base_path}/metadata.csv"
        # recreate clean dataset folder
        if os.path.exists(self.base_path):
            shutil.rmtree(self.base_path)
        os.makedirs(self.img_path, exist_ok=True)

        self.hashes = set()


    # --------------------------------
    # Input Data → API generated images
    # --------------------------------
    def generate_image_url(self):
        # random image every call
        return "https://picsum.photos/400/400"

    # --------------------------------
    # Full pipeline
    # --------------------------------
    def run(self, total=500):

        start = time.time()
        count = 0

        for i in tqdm(range(total)):

            url = self.generate_image_url()
                # -------------------------
              # ETHICS + LICENSE CHECK
               # -------------------------
            if not is_allowed_source(url):
                continue

            try:
                r = requests.get(url, timeout=5)
                content = r.content
            except:
                continue

            # Filtering & Validation
            if not validate_image(content):
                continue

            # duplicate removal
            h = file_hash(content)
            if h in self.hashes:
                continue
            self.hashes.add(h)

            filename = f"gallery_{count}.jpg"
            filepath = os.path.join(self.img_path, filename)

            # Dataset Storage
            with open(filepath, "wb") as f:
                f.write(content)

            write_metadata(
                self.meta_path,
                [
                    filename,
                    url,
                    time.strftime("%Y-%m-%d %H:%M:%S"),
                    self.category,
                    round(len(content)/1024, 2)
                ]
            )

            count += 1

        end = time.time()

        print("\n====== GALLERY SCRAPER REPORT ======")
        print("Total images:", count)
        print("Time:", round(end-start, 2), "seconds")
        print("Rate:", round(count/((end-start)/3600), 2), "samples/hour")
