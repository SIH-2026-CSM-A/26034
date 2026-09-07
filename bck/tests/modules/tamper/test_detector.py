"""Tests for tamper detection algorithms."""

import cv2
import numpy as np
import pytest
from pydantic import ValidationError

from app.contracts import EvidenceProvider, ExtractedSpan, Point
from app.modules.tamper.detector import (
    PRIOR_CONFLICTING_MRP_PROBABILITY,
    PRIOR_STICKER_OVERLAY_PROBABILITY,
    _extract_mrp_value,
    detect_conflicting_mrps,
    detect_sticker_overlay,
)
from app.modules.tamper.domain import TamperDetectionResult


def test_detect_conflicting_mrps_no_mrps():
    spans = [
        ExtractedSpan(
            span_id="s1",
            text="Net Wt 100g",
            polygon=((0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)),
            confidence=0.9,
            source_provider=EvidenceProvider.PADDLEOCR,
            region_id="panel",
        )
    ]
    assert detect_conflicting_mrps(spans) == []


def test_detect_conflicting_mrps_one_mrp():
    spans = [
        ExtractedSpan(
            span_id="s1",
            text="MRP Rs. 100",
            polygon=((0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)),
            confidence=0.9,
            source_provider=EvidenceProvider.PADDLEOCR,
            region_id="mrp",
        )
    ]
    assert detect_conflicting_mrps(spans) == []


def test_detect_conflicting_mrps_matching_mrps():
    spans = [
        ExtractedSpan(
            span_id="s1",
            text="MRP Rs. 100.00",
            polygon=((0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)),
            confidence=0.9,
            source_provider=EvidenceProvider.PADDLEOCR,
            region_id="mrp",
        ),
        ExtractedSpan(
            span_id="s2",
            text="M.R.P. 100",
            polygon=((20.0, 0.0), (30.0, 0.0), (30.0, 10.0), (20.0, 10.0)),
            confidence=0.9,
            source_provider=EvidenceProvider.PADDLEOCR,
            region_id="mrp",
        ),
    ]
    assert detect_conflicting_mrps(spans) == []


def test_detect_conflicting_mrps_conflicting_mrps():
    span1 = ExtractedSpan(
        span_id="s1",
        text="MRP Rs. 100",
        polygon=((0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)),
        confidence=0.9,
        source_provider=EvidenceProvider.PADDLEOCR,
        region_id="mrp",
    )
    span2 = ExtractedSpan(
        span_id="s2",
        text="MRP Rs. 150",
        polygon=((20.0, 0.0), (30.0, 0.0), (30.0, 10.0), (20.0, 10.0)),
        confidence=0.9,
        source_provider=EvidenceProvider.PADDLEOCR,
        region_id="mrp",
    )
    results = detect_conflicting_mrps([span1, span2])
    assert len(results) == 2
    assert all(r.probability == PRIOR_CONFLICTING_MRP_PROBABILITY for r in results)
    assert results[0].region == span1.polygon
    assert results[1].region == span2.polygon


def test_detect_conflicting_mrps_unit_sale_price_excluded():
    span_mrp = ExtractedSpan(
        span_id="s1",
        text="MRP Rs. 100",
        polygon=((0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)),
        confidence=0.9,
        source_provider=EvidenceProvider.PADDLEOCR,
        region_id="mrp",
    )
    span_usp = ExtractedSpan(
        span_id="s2",
        text="Rs. 10 per 10g",
        polygon=((20.0, 0.0), (30.0, 0.0), (30.0, 10.0), (20.0, 10.0)),
        confidence=0.9,
        source_provider=EvidenceProvider.PADDLEOCR,
        region_id="unit_sale_price",
    )
    assert detect_conflicting_mrps([span_mrp, span_usp]) == []


def test_detect_conflicting_mrps_number_parsing_with_non_mrp_text():
    span1 = ExtractedSpan(
        span_id="s1",
        text="MRP Rs. 100 Net Wt 250g",
        polygon=((0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)),
        confidence=0.9,
        source_provider=EvidenceProvider.PADDLEOCR,
        region_id="mrp",
    )
    span2 = ExtractedSpan(
        span_id="s2",
        text="M.R.P. 100.00",
        polygon=((20.0, 0.0), (30.0, 0.0), (30.0, 10.0), (20.0, 10.0)),
        confidence=0.9,
        source_provider=EvidenceProvider.PADDLEOCR,
        region_id="mrp",
    )
    # Both normalize to 100.00 rather than concatenating 100250
    assert detect_conflicting_mrps([span1, span2]) == []


def test_extract_mrp_value_reversed_order():
    span = ExtractedSpan(
        span_id="s1",
        text="Net Wt 250g MRP Rs. 100",
        polygon=((0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)),
        confidence=0.9,
        source_provider=EvidenceProvider.PADDLEOCR,
        region_id="mrp",
    )
    assert _extract_mrp_value(span) == "100.00"


def test_detect_sticker_neighboring_text_clean():
    img = np.full((200, 200, 3), 200, dtype=np.uint8)
    cv2.putText(img, "MRP Rs. 100", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    cv2.putText(img, "Net Wt 250g", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    span = ExtractedSpan(
        span_id="s1",
        text="MRP Rs. 100",
        polygon=((10.0, 30.0), (180.0, 30.0), (180.0, 65.0), (10.0, 65.0)),
        confidence=0.9,
        source_provider=EvidenceProvider.PADDLEOCR,
        region_id="mrp",
    )
    assert detect_sticker_overlay(img, [span]) == []


def test_detect_conflicting_mrps_overlapping_providers_ignored():
    span1 = ExtractedSpan(
        span_id="s1",
        text="MRP Rs. 100",
        polygon=((0.0, 0.0), (50.0, 0.0), (50.0, 20.0), (0.0, 20.0)),
        confidence=0.95,
        source_provider=EvidenceProvider.PADDLEOCR,
        region_id="mrp",
    )
    span2 = ExtractedSpan(
        span_id="s2",
        text="MRP Rs. 100.00",
        polygon=((2.0, 1.0), (48.0, 1.0), (48.0, 19.0), (2.0, 19.0)),
        confidence=0.88,
        source_provider=EvidenceProvider.TESSERACT,
        region_id="mrp",
    )
    # Spatially overlapping readings from different providers represent the same site
    assert detect_conflicting_mrps([span1, span2]) == []


def test_detect_sticker_text_glyphs_clean_print():
    img = np.full((100, 200, 3), 200, dtype=np.uint8)
    cv2.putText(img, "MRP Rs. 100", (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    span = ExtractedSpan(
        span_id="s1",
        text="MRP Rs. 100",
        polygon=((20.0, 30.0), (180.0, 30.0), (180.0, 80.0), (20.0, 80.0)),
        confidence=0.9,
        source_provider=EvidenceProvider.PADDLEOCR,
        region_id="mrp",
    )
    assert detect_sticker_overlay(img, [span]) == []


def test_detect_sticker_hard_edge():
    img = np.full((50, 50, 3), 200, dtype=np.uint8)
    img[10:40, 10:40] = 50
    span = ExtractedSpan(
        span_id="s1",
        text="MRP 100",
        polygon=((15.0, 15.0), (35.0, 15.0), (35.0, 35.0), (15.0, 35.0)),
        confidence=0.9,
        source_provider=EvidenceProvider.PADDLEOCR,
        region_id="mrp",
    )
    results = detect_sticker_overlay(img, [span])
    assert len(results) == 1
    assert results[0].probability == PRIOR_STICKER_OVERLAY_PROBABILITY


def test_detect_sticker_printed_border():
    img = np.full((50, 50, 3), 200, dtype=np.uint8)
    # A single thin line (printed border), std will be very low
    img[10, 10:40] = 0
    span = ExtractedSpan(
        span_id="s1",
        text="MRP 100",
        polygon=((15.0, 15.0), (35.0, 15.0), (35.0, 35.0), (15.0, 35.0)),
        confidence=0.9,
        source_provider=EvidenceProvider.PADDLEOCR,
        region_id="mrp",
    )
    assert detect_sticker_overlay(img, [span]) == []


def test_detect_sticker_invalid_image_raises_value_error():
    span = ExtractedSpan(
        span_id="s1",
        text="MRP 100",
        polygon=((10.0, 10.0), (20.0, 10.0), (20.0, 20.0), (10.0, 20.0)),
        confidence=0.9,
        source_provider=EvidenceProvider.PADDLEOCR,
        region_id="mrp",
    )
    with pytest.raises(ValueError, match="Invalid or empty image"):
        detect_sticker_overlay(None, [span])  # type: ignore

    with pytest.raises(ValueError, match="Invalid or empty image"):
        detect_sticker_overlay(np.array([]), [span])


def test_tamper_result_probability_bounds_validation():
    dummy_region: tuple[Point, ...] = ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))
    res_0 = TamperDetectionResult(probability=0.0, region=dummy_region, reason="valid min")
    res_1 = TamperDetectionResult(probability=1.0, region=dummy_region, reason="valid max")
    assert res_0.probability == 0.0
    assert res_1.probability == 1.0

    with pytest.raises(ValidationError):
        TamperDetectionResult(probability=-0.1, region=dummy_region, reason="invalid low")

    with pytest.raises(ValidationError):
        TamperDetectionResult(probability=1.1, region=dummy_region, reason="invalid high")
