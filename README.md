# AI-Based Automated Framework for Dataset Accumulation

An end-to-end **AI-driven data accumulation framework** that automatically discovers webpages, scrapes images using browser automation, validates them using a **vision–language model (CLIP)**, and categorizes them into a clean, usable dataset.

This framework is designed to reduce **manual data collection effort** for computer vision and multimodal AI projects.

---

## 🚀 Key Features

- 🔍 Automated Web Discovery using intelligent search queries
- 🕸️ Universal Selenium-based image scraping (JS-rendered pages supported)
- 🧠 AI-based validation using CLIP (Vision–Language Model)
- 🗂️ Automatic dataset categorization
- 📊 Detailed pipeline execution reports
- 🔁 Modular and extensible architecture

---

## 🧱 Pipeline Architecture

```
Search Queries
     ↓
Webpage Discovery
     ↓
Dynamic Image Scraping
     ↓
Raw Image Pool
     ↓
CLIP Validation
     ↓
Clean & Categorized Dataset
```

---

## 📁 Project Structure

```
AI-Based-automated-FW-for-dataset-accumilator/
│
├── ai_pipeline_manager.py      # Pipeline controller
├── universal_scraper.py        # Dynamic image scraper
├── scraper_config.py           # Category & query configuration
├── requirements.txt
├── test_links.py               # Link discovery testing
│
├── utils/
│   ├── web_link_finder.py      # Intelligent webpage discovery
│   ├── ai_classifier.py        # CLIP-based validation
│   ├── license_check.py        # License/source filtering
│   ├── hasher.py               # Duplicate detection
│   └── metadata.py
│
├── datasets/                   # Generated datasets (gitignored)
└── venv/                       # Virtual environment (gitignored)
```

---

## ⚙️ Installation

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/rhuzaii/AI-Based-automated-FW-for-dataset-accumilator-.git
cd AI-Based-automated-FW-for-dataset-accumilator-
```

### 2️⃣ Create Virtual Environment
```bash
python -m venv venv
venv\Scripts\activate
```

### 3️⃣ Install Dependencies
```bash
pip install -r requirements.txt
```

> ⚠️ Google Chrome must be installed (used by Selenium)

---

## ▶️ Running the Pipeline

```bash
python ai_pipeline_manager.py
```

### Pipeline Stages
1. Webpage discovery
2. Image scraping
3. AI validation
4. Dataset categorization

---

## 📌 Example Output

```
Found 396 images
[DONE] Downloaded 300 Raw Images

=== PIPELINE REPORT ===
Validated & Categorized: 233
Discarded Junk: 61
Uncertain/Low Confidence: 6
```

---

## 🧠 AI Model Used

- **CLIP** – `openai/clip-vit-base-patch32`
- Vision–language similarity scoring
- Filters semantically irrelevant images

---

## 🔧 Configuration

Modify **`scraper_config.py`** to add categories or queries:

```python
CATEGORY_MAP = {
    "boarding_pass": [
        "boarding pass image",
        "flight boarding pass sample",
        "airline boarding ticket photo",
        "airport boarding pass example"
    ]
}
```

---

## 🛡️ Ethical & Legal Notice

- Scrapes publicly accessible content only
- Filters restricted domains when possible
- Intended strictly for **academic and research use**

---

## 🛠️ Future Enhancements

- Resume interrupted scraping
- Multi-label image classification
- Cloud storage integration
- Dataset versioning
- Web-based monitoring dashboard

---

## 👨‍💻 Author

**Mohammed Thaqee**  
AI / ML | Data Intelligence | Systems Engineering  

---

## ⭐ Acknowledgements

- OpenAI – CLIP Model
- HuggingFace Transformers
- Selenium WebDriver

---

## 📜 License

Released for **educational and research purposes only**.

⭐ If you find this project useful, consider giving it a star!