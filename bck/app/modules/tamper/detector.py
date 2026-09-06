"""Tamper detector functions for package scans."""

import re

import cv2
import numpy as np

from app.contracts import ExtractedSpan
from app.modules.tamper.domain import TamperDetectionResult

# Empirical defaults
CV_CANNY_LOW: int = 50
CV_CANNY_HIGH: int = 150
CV_SHADOW_GRADIENT: float = 30.0
CV_PADDING: int = 10


def _extract_mrp_value(span: ExtractedSpan) -> str | None:
    """Extracts a normalized numeric MRP value from text if present."""
    text = span.text.strip()
    if not text:
        return None

    is_mrp = bool(
        re.search(r"(?:MRP|M\.R\.P\.|Rs\.?|Rupees|INR|₹)", text, re.IGNORECASE)
        or "mrp" in span.region_id.lower()
        or "retail_sale_price" in span.region_id.lower()
    )
    if not is_mrp:
        return None

    cleaned = re.sub(r"[^\d.]", "", text).strip(".")
    if not cleaned:
        return None

    try:
        val = float(cleaned)
        return f"{val:.2f}"
    except ValueError:
        return None


def detect_conflicting_mrps(spans: list[ExtractedSpan]) -> list[TamperDetectionResult]:
    """Detects conflicting Maximum Retail Price (MRP) declarations across extracted spans.

    If multiple MRP spans exist with different values, returns a 1.0 probability tamper
    result for each conflicting span. If all MRP values match or there is <= 1 MRP,
    returns an empty list.
    """
    mrp_spans_with_values: list[tuple[ExtractedSpan, str]] = []

    for span in spans:
        val = _extract_mrp_value(span)
        if val is not None:
            mrp_spans_with_values.append((span, val))

    if len(mrp_spans_with_values) <= 1:
        return []

    values = {val for _, val in mrp_spans_with_values}

    if len(values) == 1:
        return []

    results: list[TamperDetectionResult] = []
    for span, val in mrp_spans_with_values:
        results.append(
            TamperDetectionResult(
                probability=1.0,
                region=span.polygon,
                reason=f"Conflicting MRP declaration detected: '{span.text}' (normalized: {val})",
            )
        )

    return results


def detect_sticker_overlay(
    image: np.ndarray, spans: list[ExtractedSpan]
) -> list[TamperDetectionResult]:
    """Detects physical sticker overlay tampering (step edge + drop shadow) on span crops."""
    if image is None or image.size == 0 or not spans:
        return []
    results: list[TamperDetectionResult] = []
    h, w = image.shape[:2]
    for span in spans:
        if not span.polygon:
            continue
        pts = np.array(span.polygon, dtype=np.int32)
        x0 = max(0, int(np.min(pts[:, 0])) - CV_PADDING)
        y0 = max(0, int(np.min(pts[:, 1])) - CV_PADDING)
        x1 = min(w, int(np.max(pts[:, 0])) + CV_PADDING)
        y1 = min(h, int(np.max(pts[:, 1])) + CV_PADDING)
        crop = image[y0:y1, x0:x1]
        if crop.size == 0:
            continue
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if crop.ndim == 3 else crop
        edges = cv2.Canny(gray, CV_CANNY_LOW, CV_CANNY_HIGH)
        if np.count_nonzero(edges) > 0 and float(np.std(gray)) > CV_SHADOW_GRADIENT:
            results.append(
                TamperDetectionResult(
                    probability=0.85,
                    region=span.polygon,
                    reason=f"Sticker overlay detected around span '{span.text}'",
                )
            )
    return results
