"""Tests for bilingual declarations (Devanagari/Latin) binding, pairing, and disagreement rules."""

from datetime import date

import pytest

from app.contracts import (
    DeclarationField,
    DisagreementReason,
    EvidenceProvider,
    ExtractedSpan,
    FieldState,
    Verdict,
)
from app.modules.extraction import bind_spans
from app.modules.extraction.binder import ScriptType, _preprocess_devanagari_text, detect_script
from app.pipeline.findings import build_findings
from app.pipeline.orchestrator import by_obligation
from app.pipeline.rule_findings import EvidenceContext


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


def test_bare_mulya_does_not_cause_false_mrp():
    """Verify bare मूल्य without MRP prefix/context is not mapped to RETAIL_SALE_PRICE."""
    span = _make_span("s1", "मूल्य ५० N", y0=100.0, y1=130.0)
    res = bind_spans([span])
    mrp_fields = [f for f in res.fields if f.field_type == DeclarationField.RETAIL_SALE_PRICE]
    assert len(mrp_fields) == 0


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
    assert len(res.disagreements) == 0


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
    assert len(res.disagreements) == 0


def test_devanagari_only_binding():
    s_dev = _make_span("dev1", "निवल मात्रा ५०० ग्राम", y0=100.0, y1=130.0)

    res = bind_spans([s_dev])

    assert len(res.fields) == 1
    field = res.fields[0]
    assert field.field_type == DeclarationField.NET_QUANTITY
    assert field.normalised_value == "500 g"
    assert field.span_refs == ("dev1",)
    assert len(res.disagreements) == 0


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
    assert len(res.disagreements) == 0


def test_spatial_pairing_horizontal_offset_exceeded_does_not_pair():
    """Verify pairing is rejected when horizontal offset exceeds 3.0 * max_w."""
    s_lat = _make_span("lat1", "Net Qty 500g", y0=100.0, y1=130.0, x0=10.0, x1=200.0)
    s_dev = _make_span("dev1", "निवल मात्रा ५०० ग्राम", y0=105.0, y1=135.0, x0=800.0, x1=990.0)

    res = bind_spans([s_lat, s_dev])

    assert len(res.fields) == 2
    assert set(res.fields[0].span_refs + res.fields[1].span_refs) == {"lat1", "dev1"}
    assert len(res.disagreements) == 0


def test_different_region_spans_do_not_pair():
    s_lat = _make_span("lat1", "Net Qty 500g", region_id="r1", y0=100.0, y1=130.0)
    s_dev = _make_span("dev1", "निवल मात्रा ५०० ग्राम", region_id="r2", y0=140.0, y1=170.0)

    res = bind_spans([s_lat, s_dev])

    assert len(res.fields) == 2
    assert len(res.disagreements) == 0


def test_wrong_declaration_nearby_text_does_not_pair():
    s_lat = _make_span("lat1", "Net Qty 500g", y0=100.0, y1=130.0)
    s_dev = _make_span("dev1", "MRP Rs. 100", y0=140.0, y1=170.0)

    res = bind_spans([s_lat, s_dev])

    assert len(res.fields) == 2
    types = {f.field_type for f in res.fields}
    assert types == {DeclarationField.NET_QUANTITY, DeclarationField.RETAIL_SALE_PRICE}
    assert len(res.disagreements) == 0


def test_bilingual_numeric_mismatch_creates_competing_readings():
    """EXT-007: Adjacent bilingual spans with numeric contradiction form a disagreement."""
    s_lat = _make_span("lat1", "Net Qty 500g", y0=100.0, y1=130.0)
    s_dev = _make_span("dev1", "निवल मात्रा २५० ग्राम", y0=140.0, y1=170.0)

    res = bind_spans([s_lat, s_dev])

    assert len(res.fields) == 0
    assert len(res.disagreements) == 1
    dis = res.disagreements[0]
    assert dis.field_type == DeclarationField.NET_QUANTITY
    assert dis.reason == DisagreementReason.BILINGUAL_VALUE_MISMATCH
    assert len(dis.readings) == 2
    assert dis.readings[0].normalised_value == "500 g"
    assert dis.readings[1].normalised_value == "250 g"
    assert DeclarationField.NET_QUANTITY not in [f.field_type for f in res.fields]


def test_bilingual_unit_mismatch_creates_competing_readings():
    """EXT-007: Spatially adjacent bilingual spans with unit contradiction form a disagreement."""
    s_lat = _make_span("lat1", "Net Qty 500g", y0=100.0, y1=130.0)
    s_dev = _make_span("dev1", "निवल मात्रा ५०० मिलीलीटर", y0=140.0, y1=170.0)

    res = bind_spans([s_lat, s_dev])

    assert len(res.fields) == 0
    assert len(res.disagreements) == 1
    dis = res.disagreements[0]
    assert dis.field_type == DeclarationField.NET_QUANTITY
    assert dis.reason == DisagreementReason.BILINGUAL_VALUE_MISMATCH
    assert len(dis.readings) == 2
    assert dis.readings[0].unit == "g"
    assert dis.readings[1].unit == "ml"
    assert DeclarationField.NET_QUANTITY not in [f.field_type for f in res.fields]


def test_disagreement_requires_spatial_adjacency():
    """EXT-007 Requirement 4: Different value on distant spans must NOT form a disagreement."""
    s_lat = _make_span("lat1", "Net Qty 500g", y0=100.0, y1=130.0)
    s_dev = _make_span("dev1", "निवल मात्रा २५० ग्राम", y0=600.0, y1=630.0)

    res = bind_spans([s_lat, s_dev])

    assert len(res.disagreements) == 0
    assert len(res.fields) == 2
    vals = {f.normalised_value for f in res.fields}
    assert vals == {"500 g", "250 g"}


def test_disagreement_requires_same_field_type():
    """EXT-007 Requirement 5: Different field types must NOT form a disagreement."""
    s_lat = _make_span("lat1", "Net Qty 500g", y0=100.0, y1=130.0)
    s_dev = _make_span("dev1", "MRP Rs. 250", y0=140.0, y1=170.0)

    res = bind_spans([s_lat, s_dev])

    assert len(res.disagreements) == 0
    assert len(res.fields) == 2


def test_mixed_spans_do_not_participate_in_bilingual_disagreement():
    """EXT-007 Requirement 6: MIXED script spans do not form bilingual disagreements."""
    s_mix = _make_span("mix1", "निवल मात्रा 500g", y0=100.0, y1=130.0)
    s_lat = _make_span("lat1", "Net Qty 250g", y0=140.0, y1=170.0)

    res = bind_spans([s_mix, s_lat])

    assert len(res.disagreements) == 0
    assert len(res.fields) == 2


def test_neither_spans_do_not_participate_in_bilingual_disagreement():
    """EXT-007 Requirement 7: NEITHER script spans do not form bilingual disagreements."""
    s_n1 = _make_span("n1", "12345 !!!", y0=100.0, y1=130.0)
    s_n2 = _make_span("n2", "67890 !!!", y0=140.0, y1=170.0)

    res = bind_spans([s_n1, s_n2])

    assert len(res.disagreements) == 0


def test_both_readings_survive_in_competing_readings():
    """EXT-007 Requirement 9: Both original readings survive in CompetingReadings."""
    s_lat = _make_span("lat1", "Net Qty 500g", y0=100.0, y1=130.0)
    s_dev = _make_span("dev1", "निवल मात्रा २५० ग्राम", y0=140.0, y1=170.0)

    res = bind_spans([s_lat, s_dev])

    assert len(res.disagreements) == 1
    dis = res.disagreements[0]
    span_refs_in_readings = set()
    for reading in dis.readings:
        span_refs_in_readings.update(reading.span_refs)
    assert span_refs_in_readings == {"lat1", "dev1"}


def test_contract_disjointness_invariant():
    """EXT-007 Requirement 10: Contested field_type is absent from ExtractionResult.fields."""
    s_lat = _make_span("lat1", "Net Qty 500g", y0=100.0, y1=130.0)
    s_dev = _make_span("dev1", "निवल मात्रा २५० ग्राम", y0=140.0, y1=170.0)

    res = bind_spans([s_lat, s_dev])

    fields_types = {f.field_type for f in res.fields}
    disagreements_types = {d.field_type for d in res.disagreements}
    assert fields_types.isdisjoint(disagreements_types)
    assert DeclarationField.NET_QUANTITY not in fields_types
    assert DeclarationField.NET_QUANTITY in disagreements_types


def test_downstream_routing_and_verdict():
    """EXT-007 Requirement 11, 12, 13: PIP-004 routing produces REVIEW_REQUIRED and REVIEW verdict,
    NOT FAIL and NOT INSUFFICIENT_EVIDENCE."""
    s_lat = _make_span("lat1", "Net Qty 500g", y0=100.0, y1=130.0)
    s_dev = _make_span("dev1", "निवल मात्रा २५० ग्राम", y0=140.0, y1=170.0)

    res = bind_spans([s_lat, s_dev])
    assert len(res.disagreements) == 1

    from app.modules.rules import default_rule_set_version

    contested = by_obligation(res.disagreements)
    context = EvidenceContext(
        rule_set_version=default_rule_set_version(),
        evaluation_date=date(2026, 9, 6),
        declared={},
        contested=contested,
        measurements={},
        product_category=None,
        source_is_listing=False,
        unreadable_reason=None,
    )

    from app.modules.rules import load_rules

    findings = build_findings(load_rules(), context)
    r61c_findings = [f for f in findings if f.rule_snapshot.rule_id == "R6-1-C"]

    assert len(r61c_findings) > 0
    assert all(f.state == FieldState.REVIEW_REQUIRED for f in r61c_findings)
    assert not any(f.state == FieldState.FAIL for f in r61c_findings)
    assert not any(f.state == FieldState.INSUFFICIENT_EVIDENCE for f in r61c_findings)

    from app.pipeline.verdict import derive_verdict

    verdict = derive_verdict(r61c_findings)
    assert verdict == Verdict.REVIEW


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


def test_same_field_type_agreeing_and_disagreeing_pairs():
    """Reviewer Fix: Disagreeing and agreeing bilingual pairs of same type
    must not cause CTR-006 validation error.
    """
    s_lat_a = _make_span("lat1", "Net Qty 500g", region_id="r1", y0=100.0, y1=130.0)
    s_dev_a = _make_span("dev1", "निवल मात्रा २५० ग्राम", region_id="r1", y0=140.0, y1=170.0)

    s_lat_b = _make_span("lat2", "Net Qty 500g", region_id="r1", y0=200.0, y1=230.0)
    s_dev_b = _make_span("dev2", "निवल मात्रा ५०० ग्राम", region_id="r1", y0=240.0, y1=270.0)

    res = bind_spans([s_lat_a, s_dev_a, s_lat_b, s_dev_b])

    assert len(res.disagreements) == 1
    dis = res.disagreements[0]
    assert dis.field_type == DeclarationField.NET_QUANTITY
    assert dis.reason == DisagreementReason.BILINGUAL_VALUE_MISMATCH
    assert len(dis.readings) == 2
    assert all(field.field_type != DeclarationField.NET_QUANTITY for field in res.fields)

    # Both competing readings preserved
    span_refs_in_readings = set()
    for r in dis.readings:
        span_refs_in_readings.update(r.span_refs)
    assert span_refs_in_readings == {"lat1", "dev1"}


def test_contested_type_unpaired_third_span_lands_in_unclassified():
    """Phase 4: An unpaired single span of a contested field_type lands in unclassified_spans."""
    s_lat_a = _make_span("lat1", "Net Qty 500g", region_id="r1", y0=100.0, y1=130.0)
    s_dev_a = _make_span("dev1", "निवल मात्रा २५० ग्राम", region_id="r1", y0=140.0, y1=170.0)

    s_lat_b = _make_span("lat2", "Net Qty 500g", region_id="r1", y0=200.0, y1=230.0)
    s_dev_b = _make_span("dev2", "निवल मात्रा ५०० ग्राम", region_id="r1", y0=240.0, y1=270.0)

    # Third span: Latin NET_QUANTITY, unpaired, distant (y0=700.0) so not spatially adjacent
    s_unpaired = _make_span("lat3", "Net Qty 100g", region_id="r1", y0=700.0, y1=730.0)

    res = bind_spans([s_lat_a, s_dev_a, s_lat_b, s_dev_b, s_unpaired])

    assert len(res.disagreements) == 1
    assert all(field.field_type != DeclarationField.NET_QUANTITY for field in res.fields)
    unclassified_ids = {span.span_id for span in res.unclassified_spans}
    assert "lat3" in unclassified_ids


# -----------------------------------------------------------------------------
# EXT-008: Additional Script Detection (Tamil & Bengali) Tests
# -----------------------------------------------------------------------------


def test_detect_script_ext_008_additional_scripts():
    """EXT-008: Verify Tamil and Bengali script classification."""
    # Tamil script span vs NEITHER punctuation/digits
    assert detect_script("நிகர அளவு") == ScriptType.TAMIL
    assert detect_script("நிகர அளவு 500g") == ScriptType.MIXED
    # Bengali script span vs NEITHER punctuation/digits
    assert detect_script("নীট পরিমাণ") == ScriptType.BENGALI
    assert detect_script("নীট পরিমাণ 500g") == ScriptType.MIXED
    # Tamil + Bengali multi-script span returns MIXED
    assert detect_script("நிகர அளவு নীট পরিমাণ") == ScriptType.MIXED
    # Noise/punctuation remains NEITHER
    assert detect_script("!!! --- ...") == ScriptType.NEITHER
    assert detect_script("12345 !!!") == ScriptType.NEITHER
    # Regressions
    assert detect_script("Net Qty 500g") == ScriptType.LATIN
    assert detect_script("निवल मात्रा ५०० ग्राम") == ScriptType.DEVANAGARI
    assert detect_script("Net Qty निवल मात्रा") == ScriptType.MIXED


def test_additional_script_unclassified_span_conservation():
    """Verify Tamil and Bengali spans are conserved in unclassified_spans."""
    s_tam = _make_span(
        "tam1",
        "குளிர்ந்த மற்றும் உலர்ந்த இடத்தில் நேரடியாக சூரிய ஒளி படாதவாறு வைக்கவும்",
        y0=100.0,
        y1=130.0,
    )
    s_ben = _make_span(
        "ben1",
        "সূর্যের আলো থেকে দূরে একটি ঠান্ডা ও শুষ্ক স্থানে সংরক্ষণ করুন",
        y0=140.0,
        y1=170.0,
    )
    res = bind_spans([s_tam, s_ben])

    assert len(res.fields) == 0
    assert len(res.unclassified_spans) == 2
    unclassified_ids = {s.span_id for s in res.unclassified_spans}
    assert unclassified_ids == {"tam1", "ben1"}

