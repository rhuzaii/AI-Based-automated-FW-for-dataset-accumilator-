import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel

class AIClassifier:
    def __init__(self):
        print("[AI] Loading Validation Model (CLIP)...")
        # We use a base model that is fast and accurate enough for PoC
        self.model_name = "openai/clip-vit-base-patch32"
        self.model = CLIPModel.from_pretrained(self.model_name)
        self.processor = CLIPProcessor.from_pretrained(self.model_name)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model.to(self.device)
        print(f"[AI] Model loaded on {self.device}")

    def predict(self, image_path, candidate_labels):
        """
        Compares an image against a list of text descriptions.
        """
        try:
            image = Image.open(image_path)
            
            # Prepare inputs for CLIP
            inputs = self.processor(
                text=candidate_labels, 
                images=image, 
                return_tensors="pt", 
                padding=True
            ).to(self.device)

            # Inference
            with torch.no_grad():
                outputs = self.model(**inputs)
            
            # Calculate probabilities
            logits_per_image = outputs.logits_per_image
            probs = logits_per_image.softmax(dim=1)
            
            # Get best match
            best_idx = probs.argmax().item()
            best_label = candidate_labels[best_idx]
            confidence = probs[0][best_idx].item()
            
            return best_label, confidence
            
        except Exception as e:
            # print(f"[ERR] AI failed on {image_path}: {e}")
            return None, 0.0