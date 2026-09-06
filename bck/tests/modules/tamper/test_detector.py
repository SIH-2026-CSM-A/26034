"""Tests for tamper detection algorithms."""

import numpy as np

from app.contracts import EvidenceProvider, ExtractedSpan, Point
from app.modules.tamper.detector import (
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
    assert all(r.probability == 1.0 for r in results)
    assert results[0].region == span1.polygon
    assert results[1].region == span2.polygon


def test_detect_sticker_clean_print():
    img = np.full((50, 50, 3), 200, dtype=np.uint8)
    span = ExtractedSpan(
        span_id="s1",
        text="MRP 100",
        polygon=((15.0, 15.0), (35.0, 15.0), (35.0, 35.0), (15.0, 35.0)),
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
    assert len(results) > 0
    assert results[0].probability > 0.0


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


def test_tamper_result_zero_bounds():
    dummy_region: tuple[Point, ...] = ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))
    res = TamperDetectionResult(probability=0.0, region=dummy_region, reason="test")
    assert res.probability == 0.0
