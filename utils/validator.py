from PIL import Image
import io

MIN_WIDTH = 200
MIN_HEIGHT = 200

def validate_image(content: bytes):
    try:
        img = Image.open(io.BytesIO(content))

        w, h = img.size

        if w < MIN_WIDTH or h < MIN_HEIGHT:
            return False

        return True
    except:
        return False
