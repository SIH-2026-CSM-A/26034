"""Tamper detection module public entry point."""

import numpy as np

from app.contracts import ExtractedSpan
from app.modules.tamper.detector import (
    PRIOR_CONFLICTING_MRP_PROBABILITY,
    PRIOR_STICKER_OVERLAY_PROBABILITY,
    detect_conflicting_mrps,
    detect_sticker_overlay,
)
from app.modules.tamper.domain import TamperDetectionResult

def detect_tampering(image: np.ndarray, spans: list[ExtractedSpan]) -> list[TamperDetectionResult]:
    """Public entry point for tamper detection.
    
    Expected input shape for orchestrator wiring:
        - image: np.ndarray (BGR or grayscale image array of the package scan)
        - spans: list[ExtractedSpan] (extracted text spans with polygons and text values)
        
    Returns:
        list[TamperDetectionResult]: Combined findings for conflicting MRPs and sticker overlays.
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
