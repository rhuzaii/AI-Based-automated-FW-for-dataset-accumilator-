import subprocess
import sys


def _ensure(pip_name, import_name=None):
    import importlib
    try:
        return importlib.import_module(import_name or pip_name)
    except ImportError:
        print(f"[setup] Installing '{pip_name}' …")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name, "-q"])
        return importlib.import_module(import_name or pip_name)


_ensure("torch")
_ensure("transformers")
_ensure("Pillow", "PIL")

import torch
from PIL import Image, UnidentifiedImageError
from transformers import CLIPProcessor, CLIPModel


class AIClassifier:
    MODEL_NAME = "openai/clip-vit-base-patch32"

    BATCH_SIZE = 64

    def __init__(self):
        print("[AI] Loading CLIP model")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model     = CLIPModel.from_pretrained(self.MODEL_NAME).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(self.MODEL_NAME)
        self.model.eval()
        print(f"[AI] CLIP loaded on {self.device.upper()}")

    def predict(self, image_path: str, candidate_labels: list) -> tuple:
        if not candidate_labels:
            return None, 0.0

        try:
            image = Image.open(image_path).convert("RGB")
        except (UnidentifiedImageError, FileNotFoundError, OSError):
            return None, 0.0

        try:
            # Process in batches in case label list is large
            all_probs = []
            for i in range(0, len(candidate_labels), self.BATCH_SIZE):
                batch = candidate_labels[i: i + self.BATCH_SIZE]
                inputs = self.processor(
                    text=batch,
                    images=image,
                    return_tensors="pt",
                    padding=True,
                    truncation=True,
                ).to(self.device)

                with torch.no_grad():
                    outputs = self.model(**inputs)

                # Raw logits per label in this batch
                logits = outputs.logits_per_image  # shape 
                all_probs.append(logits)

            # Concatenate batch logits and run softmax across ALL labels
            combined = torch.cat(all_probs, dim=1)          
            probs     = combined.softmax(dim=1)[0]           

            best_idx    = probs.argmax().item()
            best_label  = candidate_labels[best_idx]
            confidence  = probs[best_idx].item()

            return best_label, confidence

        except Exception as e:
            print(f"[AI] Inference error on {image_path}: {e}")
            return None, 0.0

    def batch_predict(self, image_paths: list, candidate_labels: list) -> list:
        return [self.predict(p, candidate_labels) for p in image_paths]