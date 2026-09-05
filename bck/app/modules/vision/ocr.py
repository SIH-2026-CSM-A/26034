import os
from dataclasses import dataclass

import numpy as np
import pytesseract


@dataclass
class ExtractedSpan:
    polygon: list[tuple[int, int]]
    text: str
    confidence: float


def extract_panel_text(
    image: np.ndarray, det_model_dir: str, rec_model_dir: str
) -> list[ExtractedSpan]:
    """
    PaddleOCR provider for the detected panel. Requires explicit local model paths.
    """
    if image is None or image.size == 0:
        return []

    if not os.path.isdir(det_model_dir) or not os.path.isdir(rec_model_dir):
        raise FileNotFoundError("Offline OCR model directories not found.")

    from paddleocr import PaddleOCR

    ocr = PaddleOCR(
        det_model_dir=det_model_dir,
        rec_model_dir=rec_model_dir,
        use_angle_cls=False,
        use_gpu=False,
        show_log=False,
    )

    results = ocr.ocr(image, cls=False)
    spans = []

    if not results or not results[0]:
        return spans

    for line in results[0]:
        polygon = [(int(pt[0]), int(pt[1])) for pt in line[0]]
        text = line[1][0]
        confidence = float(line[1][1])
        spans.append(ExtractedSpan(polygon=polygon, text=text, confidence=confidence))

    return spans


def extract_mrp_quantity(crop: np.ndarray) -> str:
    """
    Tesseract re-pass strictly on MRP/net-quantity crops.
    """
    if crop is None or crop.size == 0:
        return ""

    # Character whitelist scoped to MRP/net-quantity values: digits, currency and
    # unit tokens (Rs, kg, ml, g), decimal point, slash, hyphen. Deliberately
    # excludes letters not needed for numeric declarations to reduce
    # misread risk.
    custom_config = r'-c tessedit_char_whitelist="0123456789.Rskgmlg/-"'
    text = pytesseract.image_to_string(crop, config=custom_config)
    return text.strip()
