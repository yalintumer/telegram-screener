import re
from PIL import Image, ImageFilter, ImageOps
import pytesseract

TICKER_REGEX = re.compile(r'\b[A-Z]{2,5}\b')

def extract_tickers(img_path: str):
    img = Image.open(img_path)
    gray = ImageOps.grayscale(img)
    sharp = gray.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
    txt = pytesseract.image_to_string(sharp)
    raw = set(TICKER_REGEX.findall(txt))
    # İstenmeyen kısa kelimeleri filtreleyebilirsin
    return sorted(raw)