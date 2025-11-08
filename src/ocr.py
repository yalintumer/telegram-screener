import re
from PIL import Image, ImageFilter, ImageOps, ImageEnhance
import pytesseract
from typing import List, Set, Dict
from .logger import logger
from .exceptions import OCRError

TICKER_REGEX = re.compile(r"\b[A-Z]{2,5}\b")

# Extended blacklist of common OCR false positives
BLACKLIST = {
    "VOLUME", "CHANGE", "BUY", "SELL", "OPEN", "CLOSE", "PRICE", "NAME", "SYMBOL",
    "HIGH", "LOW", "MARKET", "CAP", "SECTOR", "INDUSTRY", "COUNTRY",
    "THE", "AND", "FOR", "WITH", "FROM", "THIS", "THAT", "HAVE", "BEEN",
    "RATING", "NEUTRAL", "STRONG", "WEAK", "VALUE", "GROWTH", "BASIC",
    "FILTER", "SCREENER", "STOCKS", "CHART", "VIEW", "SAVE", "LOAD"
}

# Common OCR character corrections
OCR_CORRECTIONS: Dict[str, str] = {
    "0": "O",
    "1": "I", 
    "5": "S",
    "8": "B",
}


def configure_tesseract(path: str | None = None, lang: str = "eng"):
    """Configure tesseract executable path"""
    if path:
        pytesseract.pytesseract.tesseract_cmd = path
    logger.info("tesseract.configured", path=path or "default", lang=lang)


def _preprocess(img_path: str, scale_factor: int = 3) -> Image.Image:
    """
    Simplified preprocessing - sometimes less is more!
    
    Steps:
    1. Moderate upscaling (3x)
    2. Grayscale
    3. Light contrast boost
    4. Simple threshold
    
    Args:
        img_path: Path to image
        scale_factor: How much to upscale (default 3x)
    """
    try:
        img = Image.open(img_path)
        original_size = img.size
        
        # Moderate upscaling
        new_width = img.width * scale_factor
        new_height = img.height * scale_factor
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        logger.debug("ocr.upscaled", from_size=original_size, to_size=img.size, factor=scale_factor)
        
        # Convert to grayscale
        gray = ImageOps.grayscale(img)
        
        # Light contrast enhancement
        contrast = ImageEnhance.Contrast(gray)
        gray = contrast.enhance(1.5)
        
        # Simple binary threshold with inverted logic for light backgrounds
        # TradingView has dark text on light background
        threshold = 200  # Higher threshold for light backgrounds
        gray = gray.point(lambda x: 0 if x > threshold else 255, mode='1')
        gray = gray.convert('L')
        
        logger.debug("ocr.preprocessed", image=img_path, final_size=gray.size)
        return gray
        
    except Exception as e:
        logger.error("ocr.preprocess_error", error=str(e))
        raise OCRError(f"Image preprocessing failed: {e}")


def _correct_ocr_errors(text: str) -> str:
    """Apply common OCR error corrections"""
    for wrong, correct in OCR_CORRECTIONS.items():
        text = text.replace(wrong, correct)
    return text


def _validate_ticker(ticker: str) -> bool:
    """Validate if string looks like a real ticker"""
    if len(ticker) < 2 or len(ticker) > 5:
        return False
    if ticker in BLACKLIST:
        return False
    # Must be all uppercase letters
    if not ticker.isalpha():
        return False
    # Check for common OCR garbage patterns
    if ticker.count(ticker[0]) == len(ticker):  # All same letter (e.g., "AAAA")
        return False
    return True


def extract_tickers(img_path: str, config: str = "--psm 6") -> List[str]:
    """
    Extract ticker symbols from screenshot with advanced processing
    
    Args:
        img_path: Path to screenshot
        config: Tesseract config string
            --psm 6: Assume uniform block of text
            --psm 11: Sparse text
            --psm 3: Fully automatic (default)
    
    Returns:
        List of validated ticker symbols
        
    Raises:
        OCRError: If extraction fails
    """
    try:
        logger.info("ocr.start", image=img_path, config=config)
        
        # Preprocess image
        processed = _preprocess(img_path)
        
        # Run OCR
        txt = pytesseract.image_to_string(processed, config=config, lang="eng")
        
        # Apply corrections
        txt = _correct_ocr_errors(txt)
        
        logger.debug("ocr.raw_text", length=len(txt), preview=txt[:200])
        
        # Extract potential tickers
        raw: Set[str] = set(TICKER_REGEX.findall(txt))
        
        # Validate each ticker
        tickers = [t for t in raw if _validate_ticker(t)]
        tickers.sort()
        
        logger.info("ocr.complete", 
                   raw_count=len(raw),
                   filtered_count=len(tickers),
                   tickers=tickers)
        
        return tickers
        
    except pytesseract.TesseractError as e:
        logger.error("ocr.tesseract_error", error=str(e))
        raise OCRError(f"Tesseract OCR failed: {e}")
    except Exception as e:
        logger.error("ocr.error", error=str(e))
        raise OCRError(f"OCR extraction failed: {e}")
