"""OCR using PaddleOCR. Graceful fallback if not available."""
from __future__ import annotations

import logging
from threading import Lock

from app.config import settings

logger = logging.getLogger(__name__)

_ocr_model = None
_ocr_lock = Lock()
_ocr_load_failed = False


def _get_ocr():
    """Lazy-load PaddleOCR."""
    global _ocr_model, _ocr_load_failed
    if _ocr_load_failed or not settings.enable_ocr:
        return None
    with _ocr_lock:
        if _ocr_model is None:
            try:
                logger.info("Loading PaddleOCR (en)...")
                from paddleocr import PaddleOCR
                _ocr_model = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
                logger.info("PaddleOCR loaded.")
            except Exception as e:
                logger.warning("Could not load PaddleOCR: %s. OCR disabled.", e)
                _ocr_load_failed = True
                _ocr_model = None
    return _ocr_model


def extract_text(image_path: str) -> str:
    """
    Run OCR on an image file and return the concatenated text.

    Returns:
        Extracted text, or empty string if OCR is disabled or fails.
    """
    ocr = _get_ocr()
    if ocr is None:
        return ""

    try:
        result = ocr.ocr(image_path, cls=True)
        if not result or not result[0]:
            return ""
        # Each entry is [box, (text, confidence)]
        texts = [line[1][0] for line in result[0] if line[1][1] > 0.6]
        return " ".join(texts).strip()
    except Exception as e:
        logger.warning("OCR failed on %s: %s", image_path, e)
        return ""
