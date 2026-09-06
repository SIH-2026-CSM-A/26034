"""Tamper detector functions for package scans."""

import re

import cv2
import numpy as np

from app.contracts import ExtractedSpan
from app.modules.tamper.domain import TamperDetectionResult

# Uncalibrated priors for tamper detection heuristics.
# Absolute certainty (1.0) is mathematically invalid in OCR-based evidence evaluation.
# These probability estimates represent uncalibrated expert priors for detection signals
# prior to empirical calibration against labeled dataset benchmarks.
PRIOR_CONFLICTING_MRP_PROBABILITY: float = 0.95
PRIOR_STICKER_OVERLAY_PROBABILITY: float = 0.85

# Computer vision heuristics.
# Empirical defaults awaiting dataset tuning against SIH research references.
CV_CANNY_LOW: int = 50
CV_CANNY_HIGH: int = 150
CV_STEP_DISCONTINUITY_THRESHOLD: float = 35.0
CV_PADDING: int = 10
CV_BORDER_MARGIN: int = 5
CV_SPATIAL_OVERLAP_THRESHOLD: float = 0.3


def _is_mrp_span(span: ExtractedSpan) -> bool:
    """Determines whether a span explicitly declares an MRP value per Rule 6(11).

    Excludes unit sale prices (e.g., 'per kg', 'per 10g') and discount offers.
    """
    text = span.text.strip()
    if not text:
        return False

    region_id = span.region_id.lower()
    # Exclude unit sale price or discount indicators
    exclude_patterns = (
        r"(?:per\s+|/kg|/g|/l|/ml|/unit|/pc|off\b|discount\b|save\b|unit\s+sale\s+price|usp)"
    )
    if re.search(exclude_patterns, text, re.IGNORECASE) or region_id in (
        "unit_sale_price",
        "usp",
        "discount",
    ):
        return False

    # Check for explicit MRP anchor
    mrp_text_anchor = bool(
        re.search(r"(?:M\.?R\.?P\.?|Maximum\s+Retail\s+Price)", text, re.IGNORECASE)
    )
    mrp_region_anchor = region_id in (
        "mrp",
        "m_r_p",
        "retail_sale_price",
        "maximum_retail_price",
        "max_retail_price",
    )

    return mrp_text_anchor or mrp_region_anchor


def _extract_mrp_value(span: ExtractedSpan) -> str | None:
    """Extracts a normalized numeric MRP value following the mandatory MRP anchor token.

    Requires an explicit anchor prefix (without quantifier star) to ensure the number
    following the anchor is extracted rather than arbitrary leading text numbers
    (e.g., 'Net Wt 250g MRP Rs. 100' extracts 100.00).
    """
    if not _is_mrp_span(span):
        return None

    text = span.text.strip()
    # Match price digits immediately following mandatory MRP / currency anchor
    match = re.search(
        r"(?:M\.?R\.?P\.?|Maximum\s+Retail\s+Price|₹|Rs\.?|Rupees)\s*[:.-]?\s*(?:₹|Rs\.?|Rupees)?\s*([\d,]+(?:\.\d{1,2})?)",
        text,
        re.IGNORECASE,
    )
    if not match:
        return None

    cleaned = match.group(1).replace(",", "").strip(".")
    if not cleaned:
        return None

    try:
        val = float(cleaned)
        return f"{val:.2f}"
    except ValueError:
        return None


def _spans_spatially_overlap(span_a: ExtractedSpan, span_b: ExtractedSpan) -> bool:
    """Checks if two spans spatially overlap (bounding box intersection over min area)."""
    if not span_a.polygon or not span_b.polygon:
        return False

    pts_a = np.array(span_a.polygon, dtype=np.float32)
    pts_b = np.array(span_b.polygon, dtype=np.float32)

    ax_min, ay_min = float(np.min(pts_a[:, 0])), float(np.min(pts_a[:, 1]))
    ax_max, ay_max = float(np.max(pts_a[:, 0])), float(np.max(pts_a[:, 1]))
    bx_min, by_min = float(np.min(pts_b[:, 0])), float(np.min(pts_b[:, 1]))
    bx_max, by_max = float(np.max(pts_b[:, 0])), float(np.max(pts_b[:, 1]))

    inter_xmin = max(ax_min, bx_min)
    inter_ymin = max(ay_min, by_min)
    inter_xmax = min(ax_max, bx_max)
    inter_ymax = min(ay_max, by_max)

    if inter_xmax <= inter_xmin or inter_ymax <= inter_ymin:
        return False

    inter_area = (inter_xmax - inter_xmin) * (inter_ymax - inter_ymin)
    area_a = (ax_max - ax_min) * (ay_max - ay_min)
    area_b = (bx_max - bx_min) * (by_max - by_min)
    min_area = min(area_a, area_b)

    if min_area <= 0:
        return False

    return (inter_area / min_area) >= CV_SPATIAL_OVERLAP_THRESHOLD


def detect_conflicting_mrps(spans: list[ExtractedSpan]) -> list[TamperDetectionResult]:
    """Detects conflicting Maximum Retail Price (MRP) declarations across extracted spans.

    Group candidate MRP spans by spatial overlap (bounding box intersection) so that
    overlapping readings from different OCR source providers represent the same physical
    declaration site rather than a conflict.

    Returns:
        list[TamperDetectionResult]: A list of tamper findings for conflicting MRPs.
        An empty list `[]` signifies that analysis was completed and no tampering was detected.
    """
    mrp_candidates: list[tuple[ExtractedSpan, str]] = []
    for span in spans:
        val = _extract_mrp_value(span)
        if val is not None:
            mrp_candidates.append((span, val))

    if len(mrp_candidates) <= 1:
        return []

    # Cluster candidates by spatial overlap
    clusters: list[list[tuple[ExtractedSpan, str]]] = []
    for span, val in mrp_candidates:
        assigned = False
        for cluster in clusters:
            if any(_spans_spatially_overlap(span, c_span) for c_span, _ in cluster):
                cluster.append((span, val))
                assigned = True
                break
        if not assigned:
            clusters.append([(span, val)])

    if len(clusters) <= 1:
        return []

    # Compare values across spatially distinct clusters
    cluster_values = [{val for _, val in cluster} for cluster in clusters]
    all_values = {val for c_vals in cluster_values for val in c_vals}

    if len(all_values) <= 1:
        return []

    results: list[TamperDetectionResult] = []
    for cluster in clusters:
        for span, val in cluster:
            results.append(
                TamperDetectionResult(
                    probability=PRIOR_CONFLICTING_MRP_PROBABILITY,
                    region=span.polygon,
                    reason=(
                        f"Conflicting MRP declaration detected: '{span.text}' (normalized: {val})"
                    ),
                )
            )

    return results


def detect_sticker_overlay(
    image: np.ndarray, spans: list[ExtractedSpan]
) -> list[TamperDetectionResult]:
    """Detects physical sticker overlay tampering along span crop boundaries.

    Uses directional step-discontinuity analysis comparing mean pixel intensity just inside
    the border vs. just outside the border across the four sides of the span crop boundary
    to detect true physical sticker paper edges while rejecting neighboring text glyphs.

    Returns:
        list[TamperDetectionResult]: A list of tamper findings for detected sticker overlays.
        An empty list `[]` signifies that analysis was completed and no tampering was detected.

    Raises:
        ValueError: If `image` is None or has size 0.
    """
    if image is None or image.size == 0:
        raise ValueError("Invalid or empty image provided for tamper detection")

    if not spans:
        return []

    results: list[TamperDetectionResult] = []
    h, w = image.shape[:2]

    for span in spans:
        if not span.polygon:
            continue
        pts = np.array(span.polygon, dtype=np.int32)
        px_min, py_min = int(np.min(pts[:, 0])), int(np.min(pts[:, 1]))
        px_max, py_max = int(np.max(pts[:, 0])), int(np.max(pts[:, 1]))

        x0 = max(0, px_min - CV_PADDING)
        y0 = max(0, py_min - CV_PADDING)
        x1 = min(w, px_max + CV_PADDING)
        y1 = min(h, py_max + CV_PADDING)

        crop = image[y0:y1, x0:x1]
        if crop.size == 0 or crop.shape[0] < 10 or crop.shape[1] < 10:
            continue

        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if crop.ndim == 3 else crop.copy()
        ch, cw = gray.shape[:2]

        m = min(CV_BORDER_MARGIN, min(ch, cw) // 4)
        if m < 2:
            continue

        # Directional step-discontinuity analysis:
        # Compare mean pixel intensity just inside vs just outside perimeter borders.
        # Gradient thresholds and border margin parameters are uncalibrated heuristics
        # awaiting empirical dataset tuning against SIH research references.
        sides = [
            (gray[0:m, :], gray[m : 2 * m, :]),  # Top
            (gray[ch - m : ch, :], gray[ch - 2 * m : ch - m, :]),  # Bottom
            (gray[:, 0:m], gray[:, m : 2 * m]),  # Left
            (gray[:, cw - m : cw], gray[:, cw - 2 * m : cw - m]),  # Right
        ]

        edges = cv2.Canny(gray, CV_CANNY_LOW, CV_CANNY_HIGH)

        has_sticker_edge = False
        for outer, inner in sides:
            if outer.size == 0 or inner.size == 0:
                continue
            mean_outer = float(np.mean(outer))
            mean_inner = float(np.mean(inner))
            step_diff = abs(mean_outer - mean_inner)

            if step_diff > CV_STEP_DISCONTINUITY_THRESHOLD and np.count_nonzero(edges) > 0:
                has_sticker_edge = True
                break

        if has_sticker_edge:
            results.append(
                TamperDetectionResult(
                    probability=PRIOR_STICKER_OVERLAY_PROBABILITY,
                    region=span.polygon,
                    reason=f"Sticker overlay detected around span '{span.text}'",
                )
            )

    return results
