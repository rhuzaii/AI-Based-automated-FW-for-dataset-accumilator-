"""
utils/hasher.py
Perceptual hash-based duplicate image detection.
Prevents the same coupon image from appearing twice in the dataset.
"""

import logging
from pathlib import Path

from PIL import Image
import imagehash

logger = logging.getLogger(__name__)


class DuplicateDetector:
    """
    Uses average-hash (aHash) to detect visually duplicate images.
    A lower `threshold` means stricter deduplication (0 = exact match only).
    """

    def __init__(self, threshold: int = 5):
        self.threshold = threshold
        self._seen_hashes: list[imagehash.ImageHash] = []

    def is_duplicate(self, image_path: Path) -> bool:
        """Return True if the image is a near-duplicate of one already seen."""
        try:
            img = Image.open(image_path).convert("RGB")
            h = imagehash.average_hash(img)
        except Exception as e:
            logger.warning(f"[Hasher] Cannot hash {image_path.name}: {e}")
            return False  # treat unreadable as non-duplicate (will fail later)

        for seen in self._seen_hashes:
            if abs(h - seen) <= self.threshold:
                logger.debug(f"[Hasher] Duplicate detected: {image_path.name}")
                return True

        self._seen_hashes.append(h)
        return False

    def reset(self):
        self._seen_hashes.clear()
