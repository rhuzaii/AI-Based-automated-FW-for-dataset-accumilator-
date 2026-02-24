import re
import hashlib
import mimetypes
import random
from pathlib import Path

from PIL import Image

SUPPORTED_EXT = {".jpg", ".jpeg", ".png"}
MIN_IMAGE_PX  = 150          # minimum width AND height to accept an image

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
]

# Duplicate tracker 
_seen_hashes: set = set()


def file_hash(content: bytes) -> str:
    return hashlib.md5(content).hexdigest()


def is_duplicate(content: bytes) -> bool:
    h = file_hash(content)
    if h in _seen_hashes:
        return True
    _seen_hashes.add(h)
    return False


def reset_seen_hashes():
    _seen_hashes.clear()


def seen_hash_count() -> int:
    return len(_seen_hashes)


def sanitize(name: str) -> str:
    return re.sub(r"[^\w\s-]", "", name).strip().replace(" ", "_").lower()


def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


def random_ua() -> str:
    return random.choice(USER_AGENTS)


# Image validation 
def is_valid_image(path: Path) -> bool:
    try:
        w, h = Image.open(path).size
        return w >= MIN_IMAGE_PX and h >= MIN_IMAGE_PX
    except Exception:
        return False


def convert_to_jpg(path: Path) -> Path:
    if path.suffix.lower() in SUPPORTED_EXT:
        return path
    try:
        img = Image.open(path).convert("RGB")
        new = path.with_suffix(".jpg")
        img.save(new, "JPEG", quality=92)
        path.unlink()
        print(f"       Converted {path.name} → {new.name}")
        return new
    except Exception as e:
        print(f"       Conversion failed ({path.name}): {e}")
        return path


def ext_from_content_type(content_type: str) -> str:
    ct  = content_type.split(";")[0].strip()
    ext = mimetypes.guess_extension(ct) or ".jpg"
    ext = ext.replace(".jpe", ".jpg").replace(".jpeg", ".jpg")
    return ext if ext in SUPPORTED_EXT else ".jpg"
