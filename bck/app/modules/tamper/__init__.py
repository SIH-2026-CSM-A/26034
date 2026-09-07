"""Tamper detection module for LegalMetrix AI.

Exposes public entry point detect_tampering and underlying detection services.
"""

import numpy as np

from app.contracts import ExtractedSpan
from app.modules.tamper.detector import (
    PRIOR_CONFLICTING_MRP_PROBABILITY,
    PRIOR_STICKER_OVERLAY_PROBABILITY,
    detect_conflicting_mrps,
    detect_sticker_overlay,
)
from app.modules.tamper.domain import TamperDetectionResult


def detect_tampering(
    image: np.ndarray,
    spans: list[ExtractedSpan],
) -> list[TamperDetectionResult]:
    """Detect tampering in the image based on extracted spans.

    Delegates to conflicting MRP detection and sticker overlay detection.
    """
    results: list[TamperDetectionResult] = []
    results.extend(detect_conflicting_mrps(spans))
    results.extend(detect_sticker_overlay(image, spans))
    return results


__all__ = [
    "detect_tampering",
    "detect_conflicting_mrps",
    "detect_sticker_overlay",
    "PRIOR_CONFLICTING_MRP_PROBABILITY",
    "PRIOR_STICKER_OVERLAY_PROBABILITY",
]
