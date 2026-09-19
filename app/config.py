"""Upload limits and bounded generation length; OCR_MAX_LENGTH overrides the legacy alias."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODEL_ID = "baidu/Unlimited-OCR"
MODEL_REVISION = os.environ.get("UNO_MODEL_REVISION", "main")
MAX_UPLOAD_BYTES = int(os.environ.get("UNO_MAX_UPLOAD_BYTES", "0"))
PDF_DPI = int(os.environ.get("UNO_PDF_DPI", "150"))
if MAX_UPLOAD_BYTES < 0 or not 36 <= PDF_DPI <= 600:
    raise ValueError("UNO_MAX_UPLOAD_BYTES must be >= 0; UNO_PDF_DPI must be 36-600")
MAX_IMAGE_PIXELS = 25_000_000
MAX_LENGTH = int(os.environ.get("OCR_MAX_LENGTH", os.environ.get("UNO_MAX_LENGTH", "16384")))
if not 1024 <= MAX_LENGTH <= 32768:
    raise ValueError("OCR_MAX_LENGTH must be between 1024 and 32768")
