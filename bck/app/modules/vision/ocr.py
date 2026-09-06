import os
import re
import uuid
from dataclasses import dataclass
from typing import Any

import numpy as np
import pytesseract

from app.contracts import EvidenceProvider, ExtractedSpan

DEFAULT_REPASS_WHITELIST = (
    "0123456789.,/-₹RsMPkgmlL"  # digits, currency tokens and unit letters for MRP and net quantity.
)


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


def _extract_numeric_value(text: str) -> str:
    """Robustly extracts the numeric value by stripping all non-digit and non-decimal characters.

    Handles currency symbols (₹, Rs) and abbreviations safely.
    """
    if not text:
        return ""
    # Keep only digits and decimal points
    cleaned = re.sub(r"[^\d.]", "", text)
    # If multiple dots exist (e.g. malformed), keep standard float formatting or first token
    parts = cleaned.split(".")
    if len(parts) > 2:
        return ""
    return cleaned.strip(".")


def arbitrate_mrp(
    primary_text: str,
    secondary_text: str,
    span_id: str | None = None,
    primary_reading: ExtractedSpan | None = None,
) -> ArbitrationResult:
    """Arbitrates between primary and secondary readings.

    Compares normalized numeric values to avoid false discrepancies on ₹ vs Rs.
    """
    pt = primary_text.strip()
    tt = secondary_text.strip()

    val_pt = _extract_numeric_value(pt)
    val_tt = _extract_numeric_value(tt)

    if val_pt and val_pt == val_tt:
        return ArbitrationResult(
            primary_text=pt,
            secondary_text=tt,
            needs_review=False,
            agreed_text=pt,
            span_id=span_id,
            primary_reading=primary_reading,
        )

    return ArbitrationResult(
        primary_text=pt,
        secondary_text=tt,
        needs_review=True,
        agreed_text=None,
        span_id=span_id,
        primary_reading=primary_reading,
    )


def _parse_paddle_results(results: Any) -> list[ExtractedSpan]:
    """Parses PaddleOCR 3.x output formats (dict or object) into ExtractedSpan objects."""
    spans: list[ExtractedSpan] = []
    if not results:
        return spans

    items = results if isinstance(results, list) else [results]

    for item in items:
        if item is None:
            continue

        if isinstance(item, dict) and "dt_polys" in item:
            polys = item.get("dt_polys")
            texts = item.get("rec_texts")
            scores = item.get("rec_scores")
        elif hasattr(item, "dt_polys") and hasattr(item, "rec_texts"):
            polys = item.dt_polys
            texts = item.rec_texts
            scores = item.rec_scores
        else:
            raise TypeError(f"Unsupported PaddleOCR result type: {type(item)}")

        if polys is None or texts is None or scores is None:
            raise ValueError("Missing required fields in PaddleOCR result")

        for poly, text, score in zip(polys, texts, scores, strict=True):
            if score is None:
                raise ValueError("OCR confidence score cannot be None")
            pts = [(int(pt[0]), int(pt[1])) for pt in poly]
            spans.append(
                ExtractedSpan(
                    span_id=str(uuid.uuid4()),
                    region_id="frame",
                    polygon=pts,
                    text=str(text),
                    confidence=float(score),
                    source_provider=EvidenceProvider.PADDLEOCR,
                )
            )
    return spans


def extract_panel_text(
    image: np.ndarray, text_detection_model_dir: str, text_recognition_model_dir: str
) -> list[ExtractedSpan]:
    """PaddleOCR 3.x provider for the detected panel."""
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

    results = ocr.predict(image) if hasattr(ocr, "predict") else ocr.ocr(image, cls=False)
    return _parse_paddle_results(results)


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
    """Wires the pipeline: crops the bounding box, runs Tesseract, and returns arbitration.

    Note: For MRP and net-quantity spans only.
    """
    if not primary_span.polygon or len(primary_span.polygon) < 3:
        return arbitrate_mrp(
            primary_text=primary_span.text,
            secondary_text="",
            span_id=primary_span.span_id,
            primary_reading=primary_span,
        )

    pts = np.array(primary_span.polygon)
    x_min = int(np.max([0, np.min(pts[:, 0])]))
    y_min = int(np.max([0, np.min(pts[:, 1])]))
    x_max = int(np.max(pts[:, 0]))
    y_max = int(np.max(pts[:, 1]))

    crop = image[y_min:y_max, x_min:x_max]
    secondary_text = extract_mrp_quantity(crop, tessdata_dir)

    return arbitrate_mrp(
        primary_text=primary_span.text,
        secondary_text=secondary_text,
        span_id=primary_span.span_id,
        primary_reading=primary_span,
    )
