import os
import shutil
from tqdm import tqdm
from utils.ai_classifier import AIClassifier
from utils.metadata import write_metadata
import time

# --- STAGE 3 CONFIGURATION: CATEGORIES ---
CATEGORIES = {
    "events": [
        "wedding invitation card", "birthday party invitation", 
        "business event poster", "party flyer", "save the date card"
    ],
    "coupons": [
        "shopping discount coupon", "sale banner percentage off", 
        "promo code voucher", "e-commerce deal offer"
    ],
    "gallery": [
        "nature landscape photo", "portrait photography", "city architecture",
        "stock photo of objects", "artistic wallpaper"
    ],
    "boarding_pass": [
        "airline boarding pass document", 
        "flight ticket with barcode", 
        "airport boarding pass stub", 
        "paper flight ticket",
        "mobile boarding pass screen",
        "passport and boarding pass"
    ]
}

# --- STAGE 2 CONFIGURATION: JUNK FILTERS ---
JUNK_LABELS = [
    # General Junk
    "website login screen", "loading spinner icon", "website logo", 
    "plain white background", "error message text", "blurry unrecognizable image",
    
    # Boarding Pass Specific Junk (Things to ignore)
    "airplane flying in sky", "airport runway view", "suitcase luggage", 
    "person sleeping in airport", "airplane window view", "traveler selfie"
]

def run_ai_pipeline():
    raw_folder = "datasets/raw_incoming"
    if not os.path.exists(raw_folder) or not os.listdir(raw_folder):
        print("[ERR] No raw data found. Run Universal Scraper first.")
        return

    print("\n[STAGE 2 & 3] Starting AI Validation & Categorization...")
    classifier = AIClassifier() # Loads CLIP Model
    
    # Flatten categories for the AI
    label_to_category = {}
    all_descriptions = []
    
    for category, descriptions in CATEGORIES.items():
        for desc in descriptions:
            label_to_category[desc] = category
            all_descriptions.append(desc)
            
    # Add Junk filters (Stage 2)
    all_descriptions.extend(JUNK_LABELS)

    files = os.listdir(raw_folder)
    print(f"[INFO] Processing {len(files)} raw images...")

    stats = {"valid": 0, "junk": 0, "uncertain": 0}

    for filename in tqdm(files):
        filepath = os.path.join(raw_folder, filename)
        
        try:
            # AI Inference
            best_desc, score = classifier.predict(filepath, all_descriptions)
            
            target_folder = ""
            final_category = ""
            
            # --- STAGE 2: VALIDATION ---
            if best_desc in JUNK_LABELS:
                target_folder = "datasets/_discarded_junk"
                final_category = "junk"
                stats["junk"] += 1
            
            # --- STAGE 3: AUTO-CATEGORIZATION ---
            elif score < 0.22:
                target_folder = "datasets/_uncertain"
                final_category = "uncertain"
                stats["uncertain"] += 1
            else:
                final_category = label_to_category[best_desc]
                target_folder = f"datasets/{final_category}/images"
                stats["valid"] += 1

            # Move File
            os.makedirs(target_folder, exist_ok=True)
            new_path = os.path.join(target_folder, filename)
            shutil.move(filepath, new_path)
            
            # Metadata Tagging (Stage 3 API)
            if final_category not in ["junk", "uncertain"]:
                meta_path = f"datasets/{final_category}/metadata.csv"
                write_metadata(meta_path, [filename, "Auto-Scraped", "Public", time.strftime("%Y-%m-%d"), final_category, score])
            
        except Exception as e:
            print(f"[ERR] Failed on {filename}: {e}")

    print("\n=== PIPELINE REPORT ===")
    print(f"✅ Validated & Categorized: {stats['valid']}")
    print(f"❌ Discarded Junk: {stats['junk']}")
    print(f"⚠️ Uncertain/Low Confidence: {stats['uncertain']}")

if __name__ == "__main__":
    run_ai_pipeline()