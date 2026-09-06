import os
import uuid
from dataclasses import dataclass

import numpy as np
import pytesseract

from app.contracts import EvidenceProvider, ExtractedSpan


@dataclass
class ArbitrationResult:
    """Holds the result of comparing two OCR providers."""

    primary_text: str
    secondary_text: str
    needs_review: bool
    agreed_text: str | None = None


def arbitrate_mrp(primary_text: str, secondary_text: str) -> ArbitrationResult:
    """
    Arbitrates between a primary (PaddleOCR) and secondary (Tesseract) reading.
    Never picks a silent winner if they disagree on the numeric field.
    """
    pt = primary_text.strip()
    tt = secondary_text.strip()

    if pt and pt == tt:
        return ArbitrationResult(
            primary_text=pt, secondary_text=tt, needs_review=False, agreed_text=pt
        )

    return ArbitrationResult(
        primary_text=pt, secondary_text=tt, needs_review=True, agreed_text=None
    )


def extract_panel_text(
    image: np.ndarray, text_detection_model_dir: str, text_recognition_model_dir: str
) -> list[ExtractedSpan]:
    """
    PaddleOCR provider for the detected panel. Requires explicit local model paths.
    """
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
                span_id=str(uuid.uuid4()),
                region_id="panel",
                polygon=polygon,
                text=text,
                confidence=confidence,
                source_provider=EvidenceProvider.PADDLEOCR,
            )
        )

    return spans


def extract_mrp_quantity(crop: np.ndarray, tessdata_dir: str) -> str:
    """
    Tesseract re-pass strictly on MRP/net-quantity crops.
    """
    if crop is None or crop.size == 0:
        return ""

    if not os.path.isdir(tessdata_dir):
        raise FileNotFoundError("Offline OCR model directories not found.")

    # Character whitelist scoped to MRP/net-quantity values: digits, currency and
    # unit tokens (Rs, kg, ml, g), decimal point, slash, hyphen.
    custom_config = (
        rf'--tessdata-dir "{tessdata_dir}" '
        r'-c tessedit_char_whitelist="0123456789.Rskgmlg/-"'
    )
    text = pytesseract.image_to_string(crop, config=custom_config)
    return text.strip()
