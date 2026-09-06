"""Tests for bilingual declarations (Devanagari/Latin) binding and pairing rules."""

import pytest

from app.contracts import DeclarationField, EvidenceProvider, ExtractedSpan
from app.modules.extraction import bind_spans
from app.modules.extraction.binder import ScriptType, _preprocess_devanagari_text, detect_script


def _make_span(
    span_id: str,
    text: str,
    confidence: float = 0.95,
    region_id: str = "r1",
    x0: float = 10.0,
    y0: float = 10.0,
    x1: float = 200.0,
    y1: float = 40.0,
    provider: EvidenceProvider = EvidenceProvider.PADDLEOCR,
) -> ExtractedSpan:
    return ExtractedSpan(
        span_id=span_id,
        text=text,
        confidence=confidence,
        source_provider=provider,
        region_id=region_id,
        polygon=((x0, y0), (x1, y0), (x1, y1), (x0, y1)),
    )


def test_detect_script():
    assert detect_script("Net Qty 500g") == ScriptType.LATIN
    assert detect_script("निवल मात्रा ५०० ग्राम") == ScriptType.DEVANAGARI
    assert detect_script("Net Qty निवल मात्रा") == ScriptType.MIXED
    assert detect_script("12345 !!!") == ScriptType.NEITHER


def test_bare_matra_does_not_cause_false_net_quantity():
    """Verify bare मात्रा without compound context is not mapped to NET_QUANTITY."""
    span = _make_span("s1", "मात्रा ५० N", y0=100.0, y1=130.0)
    res = bind_spans([span])
    net_qty_fields = [f for f in res.fields if f.field_type == DeclarationField.NET_QUANTITY]
    assert len(net_qty_fields) == 0


def test_monolingual_latin_regression():
    s1 = _make_span("s1", "Net Qty 500g", y0=100.0, y1=130.0)
    res = bind_spans([s1])

    assert len(res.fields) == 1
    field = res.fields[0]
    assert field.field_type == DeclarationField.NET_QUANTITY
    assert field.normalised_value == "500 g"
    assert field.span_refs == ("s1",)
    assert field.parse_confidence == pytest.approx(0.95)


def test_bilingual_net_quantity_pairing():
    s_lat = _make_span("lat1", "Net Qty 500g", y0=100.0, y1=130.0)
    s_dev = _make_span("dev1", "निवल मात्रा ५०० ग्राम", y0=140.0, y1=170.0)

    res = bind_spans([s_lat, s_dev])

    assert len(res.fields) == 1
    field = res.fields[0]
    assert field.field_type == DeclarationField.NET_QUANTITY
    assert field.normalised_value == "500 g"
    assert field.span_refs == ("lat1", "dev1")
    assert field.parse_confidence == pytest.approx(0.95)


def test_devanagari_only_binding():
    s_dev = _make_span("dev1", "निवल मात्रा ५०० ग्राम", y0=100.0, y1=130.0)

    res = bind_spans([s_dev])

    assert len(res.fields) == 1
    field = res.fields[0]
    assert field.field_type == DeclarationField.NET_QUANTITY
    assert field.normalised_value == "500 g"
    assert field.span_refs == ("dev1",)


def test_unpaired_span_conservation():
    s_lat = _make_span("lat1", "Net Qty 500g", y0=100.0, y1=130.0)
    s_dev = _make_span("dev1", "निवल मात्रा ५०० ग्राम", y0=140.0, y1=170.0)
    s_unrel = _make_span("unrel1", "store away from direct sunlight", y0=300.0, y1=330.0)

    res = bind_spans([s_lat, s_dev, s_unrel])

    assert len(res.fields) == 1
    assert res.fields[0].field_type == DeclarationField.NET_QUANTITY
    assert res.fields[0].span_refs == ("lat1", "dev1")
    assert len(res.unclassified_spans) == 1
    assert res.unclassified_spans[0].span_id == "unrel1"


def test_mixed_script_single_span():
    s_mix = _make_span("mix1", "निवल मात्रा 500g", y0=100.0, y1=130.0)

    res = bind_spans([s_mix])

    assert len(res.fields) == 1
    field = res.fields[0]
    assert field.field_type == DeclarationField.NET_QUANTITY
    assert field.span_refs == ("mix1",)


def test_mixed_script_disallowed_pairing():
    s_mix = _make_span("m1", "निवल मात्रा 500g", y0=100.0, y1=130.0)
    s_lat = _make_span("l1", "Net Qty 500g", y0=140.0, y1=170.0)
    s_dev = _make_span("d1", "निवल मात्रा ५०० ग्राम", y0=180.0, y1=210.0)
    s_mix2 = _make_span("m2", "निवल मात्रा 500g", y0=220.0, y1=250.0)

    res = bind_spans([s_mix, s_lat])
    assert len(res.fields) == 2

    res2 = bind_spans([s_mix, s_mix2])
    assert len(res2.fields) == 2

    res3 = bind_spans([s_lat, s_dev])
    assert len(res3.fields) == 1
    assert res3.fields[0].span_refs == ("l1", "d1")


def test_spatial_pairing_nearby_spans():
    s_lat = _make_span("lat1", "Net Qty 500g", y0=100.0, y1=130.0)
    s_dev = _make_span("dev1", "निवल मात्रा ५०० ग्राम", y0=180.0, y1=210.0)

    res = bind_spans([s_lat, s_dev])

    assert len(res.fields) == 1
    assert res.fields[0].span_refs == ("lat1", "dev1")


def test_spatial_pairing_distant_spans_do_not_pair():
    s_lat = _make_span("lat1", "Net Qty 500g", y0=100.0, y1=130.0)
    s_dev = _make_span("dev1", "निवल मात्रा ५०० ग्राम", y0=600.0, y1=630.0)

    res = bind_spans([s_lat, s_dev])

    assert len(res.fields) == 2
    assert set(res.fields[0].span_refs + res.fields[1].span_refs) == {"lat1", "dev1"}


def test_spatial_pairing_horizontal_offset_exceeded_does_not_pair():
    """Verify pairing is rejected when horizontal offset exceeds 3.0 * max_w."""
    s_lat = _make_span("lat1", "Net Qty 500g", y0=100.0, y1=130.0, x0=10.0, x1=200.0)
    s_dev = _make_span("dev1", "निवल मात्रा ५०० ग्राम", y0=105.0, y1=135.0, x0=800.0, x1=990.0)

    res = bind_spans([s_lat, s_dev])

    assert len(res.fields) == 2
    assert set(res.fields[0].span_refs + res.fields[1].span_refs) == {"lat1", "dev1"}


def test_different_region_spans_do_not_pair():
    s_lat = _make_span("lat1", "Net Qty 500g", region_id="r1", y0=100.0, y1=130.0)
    s_dev = _make_span("dev1", "निवल मात्रा ५०० ग्राम", region_id="r2", y0=140.0, y1=170.0)

    res = bind_spans([s_lat, s_dev])

    assert len(res.fields) == 2


def test_wrong_declaration_nearby_text_does_not_pair():
    s_lat = _make_span("lat1", "Net Qty 500g", y0=100.0, y1=130.0)
    s_dev = _make_span("dev1", "MRP Rs. 100", y0=140.0, y1=170.0)

    res = bind_spans([s_lat, s_dev])

    assert len(res.fields) == 2
    types = {f.field_type for f in res.fields}
    assert types == {DeclarationField.NET_QUANTITY, DeclarationField.RETAIL_SALE_PRICE}


def test_bilingual_numeric_mismatch_does_not_pair():
    s_lat = _make_span("lat1", "Net Qty 500g", y0=100.0, y1=130.0)
    s_dev = _make_span("dev1", "निवल मात्रा २५० ग्राम", y0=140.0, y1=170.0)

    res = bind_spans([s_lat, s_dev])

    assert len(res.fields) == 2
    vals = {f.normalised_value for f in res.fields}
    assert vals == {"500 g", "250 g"}


def test_conservative_parse_confidence_uses_minimum():
    s_lat = _make_span("lat1", "Net Qty 500g", confidence=0.95, y0=100.0, y1=130.0)
    s_dev = _make_span("dev1", "निवल मात्रा ५०० ग्राम", confidence=0.60, y0=140.0, y1=170.0)

    res = bind_spans([s_lat, s_dev])

    assert len(res.fields) == 1
    assert res.fields[0].parse_confidence == pytest.approx(0.60)


def test_preprocessor_devanagari_token_boundary_collisions():
    assert _preprocess_devanagari_text("प्रोग्राम ५०० ग्राम") == "प्रोग्राम 500 g"
    cases = [
        ("५०० ग्राम", "500 g"),
        ("५०० किलोग्राम", "500 kg"),
        ("५०० किग्रा", "500 kg"),
        ("५०० मिलीग्राम", "500 mg"),
        ("५०० मिग्रा", "500 mg"),
        ("५०० मिलीलीटर", "500 ml"),
        ("५०० लीटर", "500 l"),
        ("१० सेमी", "10 cm"),
        ("२० मिमी", "20 mm"),
        ("१० मीटर", "10 m"),
    ]
    for orig, expected in cases:
        assert _preprocess_devanagari_text(orig) == expected


def test_span_conservation_assertion():
    s1 = _make_span("s1", "Net Qty 500g", y0=100.0, y1=130.0)
    s2 = _make_span("s2", "store away from direct sunlight", y0=200.0, y1=230.0)

    res = bind_spans([s1, s2])

    input_span_ids = {s1.span_id, s2.span_id}
    output_span_ids = set()
    for field in res.fields:
        output_span_ids.update(field.span_refs)
    for span in res.unclassified_spans:
        output_span_ids.add(span.span_id)

    assert input_span_ids == output_span_ids
