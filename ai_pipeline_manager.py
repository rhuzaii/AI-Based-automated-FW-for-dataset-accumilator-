import os
import sys
import shutil
import time
import argparse
import subprocess
from pathlib import Path


# Auto-install
def _ensure(pip_name, import_name=None):
    import importlib
    try:
        return importlib.import_module(import_name or pip_name)
    except ImportError:
        print(f"[setup] Installing '{pip_name}' …")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name, "-q"])
        return importlib.import_module(import_name or pip_name)

_ensure("tqdm")

from tqdm import tqdm
from ai_classifier import AIClassifier
from metadata import write_metadata, metadata_summary

# ─────────────────────────────────────────────────────────────────────────────
#  SHOPPING CATEGORIES
#  Each key maps to a list of CLIP text labels that describe what a VALID image
#  in that category looks like.  These labels compete against JUNK_LABELS below.
# ─────────────────────────────────────────────────────────────────────────────
CATEGORIES = {

    "product_listing": [
        "a product photo on a plain white background",
        "an ecommerce product listing photograph",
        "a retail product display image",
        "a product flat lay photo for online store",
        "a consumer product packshot",
        "a product catalog photograph",
        "a marketplace product thumbnail image",
        "a dropshipping product photo",
        "a studio product photography image",
        "a commercial product photograph with clean background",
    ],

    "clothing_apparel": [
        "a clothing item on a white background",
        "a fashion garment product listing photo",
        "a folded t-shirt or dress product image",
        "an apparel item hanging on a hanger product photo",
        "a clothing flat lay product photograph",
        "a jacket or hoodie product listing image",
        "sportswear product photo for online store",
        "ethnic wear or formal clothing product image",
        "denim jeans or knitwear product listing photo",
        "kids clothing product photograph ecommerce",
    ],

    "electronics_gadgets": [
        "a consumer electronics product on white background",
        "a smartphone or tablet product listing image",
        "a laptop computer product photo for ecommerce",
        "headphones or earbuds product photograph",
        "a smartwatch or fitness tracker product image",
        "a camera or gaming console product listing photo",
        "a bluetooth speaker product photograph",
        "a keyboard mouse or computer peripheral product image",
        "a home appliance gadget product listing",
        "a USB or portable charger product photo",
    ],

    "shoes_footwear": [
        "a pair of shoes on a white background",
        "a sneaker product listing photograph",
        "a boot or heel shoe product image",
        "a running shoe or athletic footwear product photo",
        "a sandal or flip flop product listing image",
        "a leather dress shoe product photograph",
        "a kids shoe product listing photo",
        "a platform or luxury designer shoe product image",
        "shoe sole detail product photograph",
        "a shoe box product listing image",
    ],

    "bags_accessories": [
        "a handbag or purse product photo on white background",
        "a backpack product listing image",
        "a wallet or belt product photograph",
        "sunglasses product listing photo",
        "a watch or jewelry product image",
        "a tote bag or crossbody bag product photo",
        "a cap or hat product listing photograph",
        "a necklace ring or bracelet product image",
        "a luggage or suitcase product listing photo",
        "a fashion accessory product photograph for ecommerce",
    ],

    "home_kitchen": [
        "a home goods product photo on white background",
        "a kitchen appliance product listing image",
        "cookware pots and pans product photograph",
        "a home decor item product listing photo",
        "bedding or pillow product image",
        "a lamp or lighting product photograph",
        "a coffee maker or blender product listing image",
        "an air fryer or vacuum cleaner product photo",
        "kitchen utensils product listing photograph",
        "a furniture or storage organizer product image",
    ],

    "shopping_receipt": [
        "a shopping receipt with itemised purchases",
        "a cash register paper receipt photograph",
        "a grocery store receipt close up image",
        "a point of sale thermal receipt",
        "a digital receipt or order confirmation screenshot",
        "a retail store paper receipt scan",
        "a payment receipt with total amount",
        "a checkout receipt with store name",
        "a supermarket bill receipt photograph",
        "an ecommerce order receipt email screenshot",
    ],
}

# ─────────────────────────────────────────────────────────────────────────────
#  JUNK LABELS
#  Images whose best CLIP match is one of these are discarded.
#  Tuned specifically to noise that appears when scraping shopping imagery.
# ─────────────────────────────────────────────────────────────────────────────
JUNK_LABELS = [
    # Generic web noise
    "website login screen or browser UI",
    "google search results page screenshot",
    "social media app interface screenshot",
    "loading spinner or app icon",
    "map or navigation screenshot",
    "blurry unrecognizable photograph",
    "plain white or solid color background",
    "company logo on white background",
    # People / lifestyle — not a clean product shot
    "a person wearing clothes in an outdoor photo",
    "a group of people shopping in a mall",
    "a model on a fashion runway",
    "people at a market or bazaar",
    "a person holding a shopping bag on a street",
    "crowd of shoppers in a store aisle",
    # Store environments — not a product shot
    "inside view of a retail store aisle",
    "supermarket shelves stocked with products",
    "mall interior with escalators and shops",
    "empty clothing rack in a store",
    "store display window from outside",
    # Unrelated documents
    "a boarding pass or flight ticket",
    "a travel passport or visa document",
    "a membership or loyalty card",
    "a coupon or promotional flyer",
    "a menu from a restaurant",
    # Unrelated photography
    "random street photography",
    "a food or drink photograph",
    "a landscape or nature photograph",
    "an abstract digital artwork",
    "a meme or screenshot of text",
    "an advertisement billboard",
    "generic office workspace photograph",
]

# Confidence threshold — below this score → _uncertain folder
DEFAULT_THRESHOLD = 0.23


# ─────────────────────────────────────────────────────────────────────────────
#  Pipeline (unchanged logic — only CATEGORIES + JUNK_LABELS above changed)
# ─────────────────────────────────────────────────────────────────────────────

def build_label_map() -> tuple:
    label_to_category = {}
    all_labels = []

    for category, labels in CATEGORIES.items():
        for lbl in labels:
            label_to_category[lbl] = category
            all_labels.append(lbl)

    for lbl in JUNK_LABELS:
        label_to_category[lbl] = "_junk"
        all_labels.append(lbl)

    return all_labels, label_to_category


def get_image_files(folder: str) -> list:
    exts = {".jpg", ".jpeg", ".png"}
    return [
        f for f in os.listdir(folder)
        if Path(f).suffix.lower() in exts
    ]


def run_pipeline(raw_folder: str, out_root: str, threshold: float):
    raw_path = Path(raw_folder)
    out_path = Path(out_root)

    if not raw_path.exists() or not any(raw_path.iterdir()):
        print(f"\n[ERR] No images found in '{raw_folder}'.")
        print("      Run image_scraper.py first, then re-run this pipeline.")
        return

    files = get_image_files(str(raw_path))
    if not files:
        print(f"\n[ERR] No JPG/PNG images in '{raw_folder}'.")
        return

    print(f"\n{'='*60}")
    print(f"  AI Classification Pipeline  —  Shopping Images")
    print(f"{'='*60}")
    print(f"  Raw folder  : {raw_path.resolve()}")
    print(f"  Output root : {out_path.resolve()}")
    print(f"  Images      : {len(files)}")
    print(f"  Categories  : {len(CATEGORIES)}")
    print(f"  Junk labels : {len(JUNK_LABELS)}")
    print(f"  Threshold   : {threshold}")
    print(f"{'='*60}\n")

    classifier = AIClassifier()
    all_labels, label_to_category = build_label_map()
    print(f"[INFO] {len(all_labels)} total text labels ({len(JUNK_LABELS)} junk labels)\n")

    stats = {"valid": 0, "junk": 0, "uncertain": 0, "error": 0}
    category_counts = {cat: 0 for cat in CATEGORIES}

    for filename in tqdm(files, desc="Classifying", unit="img"):
        filepath = str(raw_path / filename)

        try:
            best_label, score = classifier.predict(filepath, all_labels)

            if best_label is None:
                dest_folder = str(out_path / "_discarded_junk")
                final_cat   = "_junk"
                stats["error"] += 1

            elif label_to_category.get(best_label) == "_junk":
                dest_folder = str(out_path / "_discarded_junk")
                final_cat   = "_junk"
                stats["junk"] += 1

            elif score < threshold:
                dest_folder = str(out_path / "_uncertain")
                final_cat   = "_uncertain"
                stats["uncertain"] += 1

            else:
                final_cat   = label_to_category[best_label]
                dest_folder = str(out_path / final_cat / "images")
                stats["valid"] += 1
                category_counts[final_cat] = category_counts.get(final_cat, 0) + 1

            os.makedirs(dest_folder, exist_ok=True)
            dest_path = os.path.join(dest_folder, filename)

            if os.path.exists(dest_path):
                stem = Path(filename).stem
                ext  = Path(filename).suffix
                dest_path = os.path.join(dest_folder, f"{stem}_{int(time.time())}{ext}")

            shutil.move(filepath, dest_path)

            if final_cat not in ("_junk", "_uncertain"):
                meta_path    = str(out_path / final_cat / "metadata.csv")
                license_type = "CC/No-Copyright"
                write_metadata(meta_path, [
                    filename,
                    license_type,
                    "Classified",
                    time.strftime("%Y-%m-%d"),
                    best_label,
                    f"{score:.4f}",
                ])

        except Exception as e:
            tqdm.write(f"[ERR] {filename}: {e}")
            stats["error"] += 1

    print(f"\n{'='*60}")
    print(f"  PIPELINE REPORT  —  Shopping Images")
    print(f"{'='*60}")
    print(f"   Classified (valid)  : {stats['valid']}")
    print(f"   Uncertain (review)  : {stats['uncertain']}")
    print(f"   Discarded (junk)    : {stats['junk']}")
    print(f"   Errors              : {stats['error']}")
    print(f"{'='*60}")
    print(f"\n  Per-category breakdown:")
    for cat, cnt in category_counts.items():
        if cnt > 0:
            folder = out_path / cat / "images"
            print(f"    {cat:<25} → {cnt:>4} images  ({folder})")

    uncertain_path = out_path / "_uncertain"
    junk_path      = out_path / "_discarded_junk"
    print(f"\n  Uncertain  → {uncertain_path}")
    print(f"  Junk       → {junk_path}")
    print(f"\n  Metadata CSVs written per category.")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="AI Pipeline — classify scraped shopping images using CLIP"
    )
    parser.add_argument(
        "--raw",
        default="scraped_images/raw_incoming",
        help="Path to raw_incoming folder (default: scraped_images/raw_incoming)",
    )
    parser.add_argument(
        "--out",
        default="datasets",
        help="Root output folder for categorised images (default: datasets/)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help=f"Min CLIP confidence to accept (default: {DEFAULT_THRESHOLD})",
    )
    args = parser.parse_args()

    run_pipeline(
        raw_folder=args.raw,
        out_root=args.out,
        threshold=args.threshold,
    )


if __name__ == "__main__":
    main()