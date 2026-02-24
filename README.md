<<<<<<< HEAD
# AI Based automated FW for Dataset Accumulator

Scrapes Creative Commons images from Google Images and classifies them using CLIP.

## Project Structure

```
├── image_scraper.py        # Stage 1 — run this to scrape
├── categories.py           # Search keywords per category
├── compliance.py           # robots.txt checking + download
├── utils.py                # Duplicate detection & image helpers
├── ai_classifier.py        # Stage 2 — CLIP model wrapper
├── ai_pipeline_manager.py  # Stage 2 — run this to classify
└── metadata.py             # CSV metadata utility
```

## Setup

**1. Install dependencies**

```bash
pip install requests selenium webdriver-manager Pillow
pip install torch torchvision transformers tqdm
```

> ChromeDriver is auto-downloaded on first run.  
> CLIP model (approx 600 MB) is auto-downloaded on first pipeline run.

**Requirements:** Python 3.8+, Google Chrome, internet connection.

---

## Usage

### Stage 1 — Scrape Images

```bash
python image_scraper.py
```

Images are saved to `scraped_images/raw_incoming/`.

---

### Stage 2 — Classify Images

```bash
python ai_pipeline_manager.py
```

---

## Output

```
datasets/
├── event_poster/images/       # classified images
├── boarding_pass/images/
├── coupon/images/
├── membership_card/images/
├── gallery_image/images/
├── transport_ticket/images/
├── _uncertain/                # low confidence — review manually
└── _discarded_junk/           # wrong content — safe to delete
```

Each category also gets a `metadata.csv` with filename, license type, matched label, and confidence score.

---

## Categories

| # | Category | 
|---|----------|
| 1 | Event Poster | 
| 2 | Boarding Pass | 
| 3 | Gallery Image | 
| 4 | Coupon | 
| 5 | Membership Card | 
| 6 | Transport Ticket | 
| 7 | Custom | 
=======
# 25SE07MS_AI_Based_automated_FW_for_dataset_accumilator
SRIB-PRISM Program
>>>>>>> 7f3efcfb36f091e88385420812088f99090fc4c4
