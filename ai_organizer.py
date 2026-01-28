import os
import shutil
from tqdm import tqdm
from utils.ai_classifier import AIClassifier

# --- THE AI BRAIN CONFIGURATION ---
CATEGORIES = {
    # FORMAT: "folder_name": ["description 1", "description 2"]
    
    "events": [
        "wedding invitation card", "birthday party invitation", 
        "business event poster", "party flyer", "save the date card"
    ],
    "coupons": [
        "shopping discount coupon", "sale banner percentage off", 
        "promo code voucher", "e-commerce deal offer"
    ],
    "gallery": [
        "photograph of people", "nature landscape photo", 
        "portrait photography", "stock photo of objects"
    ],
    "boarding_pass": [
        "airline boarding pass", "flight ticket document", "airport boarding pass"
    ],
    "travel": [
        "travel itinerary document", "hotel booking confirmation", "travel reservation"
    ],
    "membership": [
        "membership identity card", "gym membership card", "loyalty club card"
    ]
}

# JUNK FILTER (If it matches these, delete it)
JUNK_DESCRIPTIONS = [
    "website login screen", "loading spinner icon", "website logo", 
    "plain white background", "error message text", "blurry unrecognizable image"
]

def organize_dataset():
    source_folder = "datasets/raw_incoming"
    if not os.path.exists(source_folder):
        print(f"[ERR] No raw data found in {source_folder}. Run mixed_scraper.py first.")
        return

    print("--- STARTING AI AUTO-CATEGORIZATION & VALIDATION ---")
    classifier = AIClassifier() # Loads CLIP
    
    # Flatten categories for the AI
    # We create a mapping: "wedding invitation" -> "events"
    label_to_category = {}
    all_descriptions = []
    
    for category, descriptions in CATEGORIES.items():
        for desc in descriptions:
            label_to_category[desc] = category
            all_descriptions.append(desc)
            
    # Add Junk descriptions to the list the AI checks
    all_descriptions.extend(JUNK_DESCRIPTIONS)

    # Scan files
    files = os.listdir(source_folder)
    print(f"[INFO] Processing {len(files)} raw images...")
    
    stats = {cat: 0 for cat in CATEGORIES}
    stats["junk"] = 0
    stats["uncertain"] = 0

    for filename in tqdm(files):
        filepath = os.path.join(source_folder, filename)
        
        try:
            # 1. AI PREDICTION
            best_desc, score = classifier.predict(filepath, all_descriptions)
            
            target_folder = ""
            
            # 2. LOGIC GATES
            
            # GATE A: Is it Junk?
            if best_desc in JUNK_DESCRIPTIONS:
                target_folder = "datasets/_trash"
                stats["junk"] += 1
                
            # GATE B: Is the confidence too low? (< 25%)
            elif score < 0.25:
                target_folder = "datasets/_uncertain"
                stats["uncertain"] += 1
                
            # GATE C: Valid Category
            else:
                category = label_to_category[best_desc]
                target_folder = f"datasets/{category}/images"
                stats[category] += 1

            # 3. MOVE FILE
            os.makedirs(target_folder, exist_ok=True)
            shutil.move(filepath, os.path.join(target_folder, filename))
            
        except Exception as e:
            print(f"[ERR] Failed on {filename}: {e}")

    print("\n=== AI PROCESSING REPORT ===")
    for cat, count in stats.items():
        print(f"  - {cat.upper()}: {count}")

if __name__ == "__main__":
    organize_dataset()