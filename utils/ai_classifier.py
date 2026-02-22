"""
utils/ai_classifier.py
CLIP-based vision-language model validator for coupon images.
Mirrors the boarding pass ai_classifier but with coupon prompts from scraper_config.
"""

import logging
from pathlib import Path
from typing import Literal

import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel

from scraper_config import CLIP_SETTINGS

logger = logging.getLogger(__name__)

ClassificationResult = Literal["validated", "uncertain", "discarded"]


class CouponCLIPClassifier:
    """
    Uses OpenAI CLIP to score images against coupon-specific text prompts.
    Images with similarity above `confidence_threshold` are validated,
    between thresholds are uncertain, and below are discarded.
    """

    def __init__(self):
        cfg = CLIP_SETTINGS
        logger.info(f"[CLIP] Loading model: {cfg['model_name']}")
        self.model = CLIPModel.from_pretrained(cfg["model_name"])
        self.processor = CLIPProcessor.from_pretrained(cfg["model_name"])
        self.model.eval()
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model.to(self.device)

        self.confidence_threshold = cfg["confidence_threshold"]
        self.uncertain_threshold = cfg["uncertain_threshold"]
        self.positive_prompts = cfg["positive_prompts"]
        self.negative_prompts = cfg["negative_prompts"]
        self.batch_size = cfg["batch_size"]

        logger.info(f"[CLIP] Running on: {self.device}")

    def _score_image(self, image: Image.Image) -> float:
        """
        Compute a net coupon relevance score for a single PIL image.
        Score = mean(positive similarities) - mean(negative similarities)
        """
        all_prompts = self.positive_prompts + self.negative_prompts
        inputs = self.processor(
            text=all_prompts,
            images=image,
            return_tensors="pt",
            padding=True,
        ).to(self.device)

        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits_per_image.softmax(dim=1).squeeze()

        n_pos = len(self.positive_prompts)
        pos_score = logits[:n_pos].mean().item()
        neg_score = logits[n_pos:].mean().item()
        return pos_score - neg_score

    def classify(self, image_path: Path) -> tuple[ClassificationResult, float]:
        """
        Classify a single image file.

        Returns:
            (result, score) where result is 'validated', 'uncertain', or 'discarded'
        """
        try:
            image = Image.open(image_path).convert("RGB")
        except Exception as e:
            logger.warning(f"[CLIP] Cannot open {image_path.name}: {e}")
            return "discarded", 0.0

        score = self._score_image(image)

        if score >= self.confidence_threshold:
            result: ClassificationResult = "validated"
        elif score >= self.uncertain_threshold:
            result = "uncertain"
        else:
            result = "discarded"

        logger.debug(f"[CLIP] {image_path.name} → {result} (score={score:.4f})")
        return result, score

    def classify_batch(
        self, image_paths: list[Path]
    ) -> list[tuple[Path, ClassificationResult, float]]:
        """
        Classify a list of image paths, returning (path, result, score) tuples.
        """
        results = []
        for path in image_paths:
            res, score = self.classify(path)
            results.append((path, res, score))
        return results
