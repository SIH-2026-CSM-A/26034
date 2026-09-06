import os
import uuid
from dataclasses import dataclass

import numpy as np
import pytesseract

from app.contracts import EvidenceProvider, ExtractedSpan

# Character whitelist scoped to MRP/net-quantity values per DoCA guidelines:
# - Digits (0-9), decimal (.), slash (/), hyphen (-) for values and dates.
# - 'M', 'P', 'R' to read the literal token "MRP".
# - '₹', 'R', 's' because retail sale price may be declared with ₹ or Rs.
# - 'k', 'g', 'm', 'l' for standard unit tokens (kg, g, mg, ml, l).
DEFAULT_REPASS_WHITELIST = "0123456789./-₹RsMPkgml"

@dataclass
class ArbitrationResult:
    """Holds the result of comparing two OCR providers."""
    primary_text: str
    secondary_text: str
    needs_review: bool
    agreed_text: str | None = None
    primary_provider: EvidenceProvider = EvidenceProvider.PADDLEOCR
    secondary_provider: EvidenceProvider = EvidenceProvider.TESSERACT
    span_id: str | None = None
    primary_reading: ExtractedSpan | None = None

def arbitrate_mrp(
    primary_text: str, 
    secondary_text: str, 
    span_id: str | None = None, 
    primary_reading: ExtractedSpan | None = None
) -> ArbitrationResult:
    """Arbitrates between a primary (PaddleOCR) and secondary (Tesseract) reading."""
    pt = primary_text.strip()
    tt = secondary_text.strip()

    if pt and pt == tt:
        return ArbitrationResult(
            primary_text=pt, secondary_text=tt, needs_review=False, agreed_text=pt,
            span_id=span_id, primary_reading=primary_reading
        )

    return ArbitrationResult(
        primary_text=pt, secondary_text=tt, needs_review=True, agreed_text=None,
        span_id=span_id, primary_reading=primary_reading
    )

def extract_panel_text(
    image: np.ndarray, text_detection_model_dir: str, text_recognition_model_dir: str
) -> list[ExtractedSpan]:
    """PaddleOCR provider for the detected panel. Requires explicit local model paths."""
    if image is None or image.size == 0:
        return []

    if not os.path.isdir(text_detection_model_dir) or not os.path.isdir(text_recognition_model_dir):
        raise FileNotFoundError("Offline OCR model directories not found.")

    from paddleocr import PaddleOCR
    ocr = PaddleOCR(
        text_detection_model_dir=text_detection_model_dir,
        text_recognition_model_dir=text_recognition_model_dir,
        use_textline_orientation=False,
        device="cpu",
    )

    if hasattr(ocr, "predict"):
        results = ocr.predict(image)
    else:
        results = ocr.ocr(image, cls=False)
        
    spans = []
    if not results or not results[0]:
        return spans

    for line in results[0]:
        polygon = [(int(pt[0]), int(pt[1])) for pt in line[0]]
        text = line[1][0]
        confidence = float(line[1][1])
        spans.append(
            ExtractedSpan(
                span_id=str(uuid.uuid4()), region_id="panel", polygon=polygon,
                text=text, confidence=confidence, source_provider=EvidenceProvider.PADDLEOCR,
            )
        )
    return spans

def extract_mrp_quantity(crop: np.ndarray, tessdata_dir: str) -> str:
    """Tesseract re-pass strictly on MRP/net-quantity crops."""
    if crop is None or crop.size == 0:
        return ""

    if not os.path.isdir(tessdata_dir):
        raise FileNotFoundError("Offline OCR model directories not found.")

    custom_config = (
        rf'--tessdata-dir "{tessdata_dir}" '
        f'-c tessedit_char_whitelist="{DEFAULT_REPASS_WHITELIST}"'
    )
    text = pytesseract.image_to_string(crop, config=custom_config)
    return text.strip()

def arbitrate_field_declaration(
    image: np.ndarray, primary_span: ExtractedSpan, tessdata_dir: str
) -> ArbitrationResult:
    """Wires the pipeline: crops the bounding box, runs Tesseract, and returns arbitration."""
    if not primary_span.polygon or len(primary_span.polygon) < 3:
        return arbitrate_mrp(primary_span.text, "", span_id=primary_span.span_id, primary_reading=primary_span)

    pts = np.array(primary_span.polygon)
    x_min, y_min = np.max([0, np.min(pts[:, 0])]), np.max([0, np.min(pts[:, 1])])
    x_max, y_max = np.max(pts[:, 0]), np.max(pts[:, 1])

    crop = image[y_min:y_max, x_min:x_max]
    secondary_text = extract_mrp_quantity(crop, tessdata_dir)
    
    return arbitrate_mrp(
        primary_text=primary_span.text, secondary_text=secondary_text,
        span_id=primary_span.span_id, primary_reading=primary_span
    )
