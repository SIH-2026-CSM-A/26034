import numpy as np

from app.contracts import ExtractedSpan
from app.modules.tamper.detector import (
    detect_conflicting_mrps,
    detect_sticker_overlay,
)
from app.modules.tamper.domain import TamperDetectionResult

PRIOR_CONFLICTING_MRP_PROBABILITY = 0.95
PRIOR_STICKER_OVERLAY_PROBABILITY = 0.85


def detect_tampering(
    image: np.ndarray,
    spans: list[ExtractedSpan],
) -> list[TamperDetectionResult]:
    """
    Public entry point for tamper module.
    Scores regions for tampering (e.g. conflicting MRP, sticker overlay)
    and returns tamper findings as evidence. Does not decide compliance.
    """
    results: list[TamperDetectionResult] = []
    results.extend(detect_conflicting_mrps(spans))
    results.extend(detect_sticker_overlay(image, spans))
    return results
