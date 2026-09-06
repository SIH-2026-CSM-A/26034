"""Tests for Rule 9(4) bilingual declarations and script detection in binder.py."""

from app.contracts import DeclarationField, EvidenceProvider, ExtractedSpan
from app.modules.extraction.binder import ScriptType, bind_spans, detect_script


def _make_span(
    span_id: str,
    text: str,
    x0: float = 100.0,
    y0: float = 100.0,
    x1: float = 300.0,
    y1: float = 140.0,
    region_id: str = "reg_1",
    confidence: float = 0.95,
) -> ExtractedSpan:
    polygon = (
        (x0, y0),
        (x1, y0),
        (x1, y1),
        (x0, y1),
    )
    return ExtractedSpan(
        span_id=span_id,
        text=text,
        polygon=polygon,
        confidence=confidence,
        source_provider=EvidenceProvider.PADDLEOCR,
        region_id=region_id,
    )


def test_detect_script():
    assert detect_script("मात्रा ५०० ग्राम") == ScriptType.DEVANAGARI
    assert detect_script("Net Qty 500g") == ScriptType.LATIN
    assert detect_script("मात्रा 500g") == ScriptType.MIXED
    assert detect_script("12345 !@#$%") == ScriptType.NEITHER


def test_monolingual_latin_regression():
    spans = [
        _make_span("s1", "Net Qty 500g", y0=100.0, y1=130.0),
        _make_span("s2", "MRP Rs. 100", y0=150.0, y1=180.0),
    ]
    res = bind_spans(spans)
    assert len(res.fields) == 2
    field_types = {f.field_type for f in res.fields}
    assert DeclarationField.NET_QUANTITY in field_types
    assert DeclarationField.RETAIL_SALE_PRICE in field_types
    assert len(res.unclassified_spans) == 0


def test_bilingual_net_quantity_pairing():
    s_lat = _make_span("lat1", "Net Qty 500g", y0=100.0, y1=130.0)
    s_dev = _make_span("dev1", "मात्रा ५०० ग्राम", y0=140.0, y1=170.0)
    res = bind_spans([s_lat, s_dev])

    assert len(res.fields) == 1
    field = res.fields[0]
    assert field.field_type == DeclarationField.NET_QUANTITY
    assert set(field.span_refs) == {"lat1", "dev1"}
    assert field.numeric_value == 500.0
    assert field.unit == "g"
    assert len(res.unclassified_spans) == 0


def test_devanagari_only_binding():
    s_dev = _make_span("dev1", "मात्रा ५०० ग्राम", y0=100.0, y1=130.0)
    res = bind_spans([s_dev])

    assert len(res.fields) == 1
    field = res.fields[0]
    assert field.field_type == DeclarationField.NET_QUANTITY
    assert field.span_refs == ("dev1",)
    assert field.numeric_value == 500.0
    assert field.unit == "g"
    assert len(res.unclassified_spans) == 0


def test_unpaired_span_conservation():
    s_known = _make_span("s1", "Net Qty 500g", y0=100.0, y1=130.0)
    s_random = _make_span("s2", "विशेष ऑफर डिस्काउंट", y0=200.0, y1=230.0)
    res = bind_spans([s_known, s_random])

    assert len(res.fields) == 1
    assert len(res.unclassified_spans) == 1
    assert res.unclassified_spans[0].span_id == "s2"

    bound_ids = {sid for f in res.fields for sid in f.span_refs}
    unclass_ids = {s.span_id for s in res.unclassified_spans}
    assert bound_ids | unclass_ids == {"s1", "s2"}
    assert bound_ids & unclass_ids == set()


def test_mixed_script_single_span():
    s_mix = _make_span("s1", "मात्रा 500g", y0=100.0, y1=130.0)
    res = bind_spans([s_mix])

    assert len(res.fields) == 1
    field = res.fields[0]
    assert field.field_type == DeclarationField.NET_QUANTITY
    assert field.span_refs == ("s1",)
    assert field.numeric_value == 500.0
    assert field.unit == "g"


def test_spatial_pairing_nearby_spans():
    s_lat = _make_span("lat1", "Net Qty 500g", y0=100.0, y1=130.0)
    s_dev = _make_span("dev1", "मात्रा ५०० ग्राम", y0=150.0, y1=180.0)
    res = bind_spans([s_lat, s_dev])

    assert len(res.fields) == 1
    assert set(res.fields[0].span_refs) == {"lat1", "dev1"}


def test_spatial_pairing_distant_spans_do_not_pair():
    s_lat = _make_span("lat1", "Net Qty 500g", y0=100.0, y1=130.0)
    s_dev = _make_span("dev1", "मात्रा ५०० ग्राम", y0=330.0, y1=360.0)
    res = bind_spans([s_lat, s_dev])

    assert len(res.fields) == 2
    assert res.fields[0].span_refs == ("lat1",)
    assert res.fields[1].span_refs == ("dev1",)


def test_wrong_declaration_nearby_text_does_not_pair():
    s_net_dev = _make_span("dev1", "मात्रा ५०० ग्राम", y0=100.0, y1=130.0)
    s_mrp_lat = _make_span("lat1", "MRP Rs. 100", y0=140.0, y1=170.0)
    res = bind_spans([s_net_dev, s_mrp_lat])

    assert len(res.fields) == 2
    types = {f.field_type: f.span_refs for f in res.fields}
    assert types[DeclarationField.NET_QUANTITY] == ("dev1",)
    assert types[DeclarationField.RETAIL_SALE_PRICE] == ("lat1",)


def test_bilingual_numeric_mismatch_does_not_pair():
    # Scenario A: Mismatching numeric values (500g vs 200g)
    s_dev = _make_span("dev1", "मात्रा ५०० ग्राम", y0=100.0, y1=130.0)
    s_lat_mismatch = _make_span("lat1", "Net Qty 200g", y0=140.0, y1=170.0)
    res1 = bind_spans([s_dev, s_lat_mismatch])

    assert len(res1.fields) == 2
    assert res1.fields[0].span_refs == ("dev1",)
    assert res1.fields[1].span_refs == ("lat1",)

    # Scenario B: One numeric value (10 cm) vs missing numeric value (10 सेमी x 20 सेमी)
    s_lat_dim = _make_span("lat2", "10 cm", y0=100.0, y1=130.0)
    s_dev_dim = _make_span("dev2", "१० सेमी x २० सेमी", y0=140.0, y1=170.0)
    res2 = bind_spans([s_lat_dim, s_dev_dim])

    pair_fields = [f for f in res2.fields if set(f.span_refs) == {"lat2", "dev2"}]
    assert len(pair_fields) == 0


def test_span_conservation_assertion():
    spans = [
        _make_span("s1", "Net Qty 500g", y0=100.0, y1=130.0),
        _make_span("s2", "मात्रा ५०० ग्राम", y0=140.0, y1=170.0),
        _make_span("s3", "MRP Rs. 100", y0=200.0, y1=230.0),
        _make_span("s4", "अनजान टेक्स्ट 123", y0=300.0, y1=330.0),
    ]
    res = bind_spans(spans)

    all_input_ids = {s.span_id for s in spans}
    bound_ids = {sid for f in res.fields for sid in f.span_refs}
    unclass_ids = {s.span_id for s in res.unclassified_spans}

    assert bound_ids | unclass_ids == all_input_ids
    assert bound_ids & unclass_ids == set()
    assert len(bound_ids) + len(unclass_ids) == len(all_input_ids)
