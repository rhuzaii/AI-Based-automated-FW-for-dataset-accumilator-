"""
utils/metadata.py
Tracks provenance, CLIP scores, and classification results for every image.
Saves to datasets/metadata.json for reproducibility and auditing.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from scraper_config import OUTPUT_SETTINGS

logger = logging.getLogger(__name__)


class MetadataTracker:
    """
    Accumulates per-image metadata and writes to a JSON file at the end.

    Record schema:
    {
        "filename":    "retail_coupon_0001.jpg",
        "source_url":  "https://...",
        "category":    "retail_coupon",
        "clip_score":  0.312,
        "result":      "validated",   // validated | uncertain | discarded | duplicate
        "timestamp":   "2025-11-01T12:34:56"
    }
    """

    def __init__(self):
        self._records: list[dict] = []
        self._output_path = Path(OUTPUT_SETTINGS["metadata_file"])
        self._output_path.parent.mkdir(parents=True, exist_ok=True)

    def add(
        self,
        filename: str,
        source_url: str,
        category: str,
        clip_score: float,
        result: str,
    ):
        self._records.append(
            {
                "filename": filename,
                "source_url": source_url,
                "category": category,
                "clip_score": round(clip_score, 5),
                "result": result,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    def save(self):
        with open(self._output_path, "w", encoding="utf-8") as f:
            json.dump(self._records, f, indent=2, ensure_ascii=False)
        logger.info(f"[Metadata] Saved {len(self._records)} records → {self._output_path}")

    @property
    def records(self) -> list[dict]:
        return self._records
