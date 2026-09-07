"""Tests for bilingual declarations (Devanagari/Latin) binding, pairing, and disagreement rules."""

from datetime import date

import pytest

from app.contracts import (
    DeclarationField,
    DisagreementReason,
    EvidenceProvider,
    ExtractedSpan,
    FieldState,
    NormalisedField,
    Verdict,
)
from app.modules.extraction import bind_spans
from app.modules.extraction.binder import (
    BboxRefusal,
    BboxRefusalReason,
    ScriptType,
    _preprocess_devanagari_text,
    bbox_refusal_officer_reason,
    detect_script,
    get_declaration_bbox,
)
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


# -----------------------------------------------------------------------------
# EXT-008: Additional Script Detection Tests (Refactored into 7 Independent Claim Tests)
# -----------------------------------------------------------------------------


def test_detect_script_ext_008_claim_1_noise():
    """Claim 1: Punctuation, digits, and noise spans classify as NEITHER."""
    assert detect_script("12345 !!!") == ScriptType.NEITHER
    assert detect_script("!!! --- ...") == ScriptType.NEITHER


def test_detect_script_ext_008_claim_2_latin_accents():
    """Claim 2: Plain/accented Latin letters (including NFD combining marks) classify as LATIN."""
    assert detect_script("Net Qty 500g") == ScriptType.LATIN
    assert detect_script("é") == ScriptType.LATIN
    assert detect_script("Café") == ScriptType.LATIN
    assert detect_script("Nestlé") == ScriptType.LATIN
    assert detect_script("München") == ScriptType.LATIN
    assert detect_script("é") == ScriptType.LATIN


def test_detect_script_ext_008_claim_3_devanagari():
    """Claim 3: Devanagari text classifies as DEVANAGARI."""
    assert detect_script("निवल मात्रा ५०० ग्राम") == ScriptType.DEVANAGARI


def test_detect_script_ext_008_claim_4_tamil():
    """Claim 4: Tamil text classifies as TAMIL."""
    assert detect_script("தமிழ்") == ScriptType.TAMIL


def test_detect_script_ext_008_claim_5_bengali():
    """Claim 5: Bengali text classifies as BENGALI."""
    assert detect_script("বাংলা") == ScriptType.BENGALI


def test_detect_script_ext_008_claim_6_unsupported():
    """Claim 6: Non-handled script letters classify as UNSUPPORTED and differ from NEITHER noise."""
    assert detect_script("నికర పరిమాణం") == ScriptType.UNSUPPORTED
    assert detect_script("ಅನುಪಾತ") == ScriptType.UNSUPPORTED
    assert detect_script("中文") == ScriptType.UNSUPPORTED
    assert detect_script("العربية") == ScriptType.UNSUPPORTED
    assert detect_script("నికర పరిమాణం") != detect_script("12345 !!!")


def test_detect_script_ext_008_claim_7_mixed():
    """Claim 7: Spans with letters from multiple recognized script categories evaluate to MIXED."""
    assert detect_script("நிகர அளவு 500g") == ScriptType.MIXED
    assert detect_script("বাংলা 500g") == ScriptType.MIXED
    assert detect_script("தமிழ் বাংলা") == ScriptType.MIXED
    assert detect_script("నికర పరిమాణం 500g") == ScriptType.MIXED
    assert detect_script("Net Qty निवल मात्रा") == ScriptType.MIXED


def test_additional_script_unclassified_span_conservation():
    """Verify Tamil, Bengali, and unsupported script spans are conserved in unclassified_spans."""
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


def test_recognized_additional_script_unnormalized_routes_to_review():
    """Verify unnormalised additional script routes to INSUFFICIENT_EVIDENCE and REVIEW."""
    from app.modules.rules import default_rule_set_version, load_rules
    from app.pipeline.orchestrator import UNBOUND_DECLARATION_REASON
    from app.pipeline.verdict import derive_verdict

    s_tam = _make_span(
        "tam1",
        "குளிர்ந்த மற்றும் உலர்ந்த இடத்தில் நேரடியாக சூரிய ஒளி படாதவாறு வைக்கவும்",
        y0=100.0,
        y1=130.0,
    )
    res = bind_spans([s_tam])

    assert len(res.fields) == 0
    assert len(res.unclassified_spans) == 1
    assert res.unclassified_spans[0].span_id == "tam1"

    context = EvidenceContext(
        rule_set_version=default_rule_set_version(),
        evaluation_date=date(2026, 9, 6),
        declared=by_obligation(res.fields),
        contested=by_obligation(res.disagreements),
        measurements={},
        product_category=None,
        source_is_listing=False,
        unreadable_reason=UNBOUND_DECLARATION_REASON,
    )

    findings = build_findings(load_rules(), context)
    assert len(findings) > 0
    assert any(f.state == FieldState.INSUFFICIENT_EVIDENCE for f in findings)
    assert all(
        f.state in (FieldState.INSUFFICIENT_EVIDENCE, FieldState.NOT_APPLICABLE) for f in findings
    )
    assert not any(f.state == FieldState.FAIL for f in findings)
    assert not any(f.state == FieldState.PASS for f in findings)

    verdict = derive_verdict(findings)
    assert verdict == Verdict.REVIEW
    assert verdict != Verdict.POTENTIAL_VIOLATION
    assert verdict != Verdict.PASS


def test_get_declaration_bbox_single_span():
    span = ExtractedSpan(
        span_id="s1",
        text="Net Qty 500g",
        confidence=0.95,
        source_provider=EvidenceProvider.PADDLEOCR,
        region_id="r1",
        polygon=((10.0, 20.0), (200.0, 20.0), (200.0, 50.0), (10.0, 50.0)),
    )
    field = NormalisedField(
        field_type=DeclarationField.NET_QUANTITY,
        span_refs=("s1",),
        normalised_value="500 g",
        parse_confidence=0.95,
    )
    bbox = get_declaration_bbox(field, [span])
    assert bbox == (10.0, 20.0, 200.0, 50.0)


def test_get_declaration_bbox_bilingual_pair():
    span1 = ExtractedSpan(
        span_id="lat1",
        text="Net Qty 500g",
        confidence=0.95,
        source_provider=EvidenceProvider.PADDLEOCR,
        region_id="r1",
        polygon=((10.0, 20.0), (200.0, 20.0), (200.0, 50.0), (10.0, 50.0)),
    )
    span2 = ExtractedSpan(
        span_id="dev1",
        text="निवल मात्रा ५०० ग्राम",
        confidence=0.95,
        source_provider=EvidenceProvider.PADDLEOCR,
        region_id="r1",
        polygon=((15.0, 60.0), (210.0, 60.0), (210.0, 90.0), (15.0, 90.0)),
    )
    field = NormalisedField(
        field_type=DeclarationField.NET_QUANTITY,
        span_refs=("lat1", "dev1"),
        normalised_value="500 g",
        parse_confidence=0.95,
    )
    bbox = get_declaration_bbox(field, [span1, span2])
    assert bbox == (10.0, 20.0, 210.0, 90.0)


def test_get_declaration_bbox_multi_line_address():
    span1 = ExtractedSpan(
        span_id="a1",
        text="Mfg by ABC Foods",
        confidence=0.95,
        source_provider=EvidenceProvider.PADDLEOCR,
        region_id="r1",
        polygon=((50.0, 100.0), (300.0, 100.0), (300.0, 130.0), (50.0, 130.0)),
    )
    span2 = ExtractedSpan(
        span_id="a2",
        text="Mumbai 400001",
        confidence=0.95,
        source_provider=EvidenceProvider.PADDLEOCR,
        region_id="r1",
        polygon=((40.0, 140.0), (280.0, 140.0), (280.0, 170.0), (40.0, 170.0)),
    )
    field = NormalisedField(
        field_type=DeclarationField.NAME_AND_ADDRESS,
        span_refs=("a1", "a2"),
        normalised_value="Mfg by ABC Foods Mumbai 400001",
        parse_confidence=0.95,
    )
    bbox = get_declaration_bbox(field, [span1, span2])
    assert bbox == (40.0, 100.0, 300.0, 170.0)


def test_get_declaration_bbox_refusal_empty_span_refs():
    field = NormalisedField.model_construct(
        field_type=DeclarationField.NET_QUANTITY,
        span_refs=(),
        normalised_value="500 g",
        parse_confidence=0.95,
    )
    result = get_declaration_bbox(field, [])
    assert isinstance(result, BboxRefusal)
    assert result.reason == BboxRefusalReason.NO_SPAN_REFS
    assert result.span_id is None


def test_get_declaration_bbox_refusal_missing_span_id():
    field = NormalisedField(
        field_type=DeclarationField.NET_QUANTITY,
        span_refs=("missing_id",),
        normalised_value="500 g",
        parse_confidence=0.95,
    )
    result = get_declaration_bbox(field, [])
    assert isinstance(result, BboxRefusal)
    assert result.reason == BboxRefusalReason.UNKNOWN_SPAN_ID
    assert result.span_id is None


def test_get_declaration_bbox_refusal_empty_polygon():
    span = ExtractedSpan.model_construct(
        span_id="s1",
        text="Net Qty 500g",
        confidence=0.95,
        source_provider=EvidenceProvider.PADDLEOCR,
        region_id="r1",
        polygon=(),
    )
    field = NormalisedField(
        field_type=DeclarationField.NET_QUANTITY,
        span_refs=("s1",),
        normalised_value="500 g",
        parse_confidence=0.95,
    )
    result = get_declaration_bbox(field, [span])
    assert isinstance(result, BboxRefusal)
    assert result.reason == BboxRefusalReason.EMPTY_POLYGON
    assert result.span_id == "s1"


def test_get_declaration_bbox_refusal_insufficient_vertices():
    span = ExtractedSpan.model_construct(
        span_id="s1",
        text="Net Qty 500g",
        confidence=0.95,
        source_provider=EvidenceProvider.PADDLEOCR,
        region_id="r1",
        polygon=((10.0, 20.0), (100.0, 20.0)),
    )
    field = NormalisedField(
        field_type=DeclarationField.NET_QUANTITY,
        span_refs=("s1",),
        normalised_value="500 g",
        parse_confidence=0.95,
    )
    result = get_declaration_bbox(field, [span])
    assert isinstance(result, BboxRefusal)
    assert result.reason == BboxRefusalReason.INSUFFICIENT_VERTICES
    assert result.span_id == "s1"


def test_get_declaration_bbox_refusal_malformed_point():
    span = ExtractedSpan.model_construct(
        span_id="s1",
        text="Net Qty 500g",
        confidence=0.95,
        source_provider=EvidenceProvider.PADDLEOCR,
        region_id="r1",
        polygon=((10.0,), (100.0, 20.0), (100.0, 50.0)),
    )
    field = NormalisedField(
        field_type=DeclarationField.NET_QUANTITY,
        span_refs=("s1",),
        normalised_value="500 g",
        parse_confidence=0.95,
    )
    result = get_declaration_bbox(field, [span])
    assert isinstance(result, BboxRefusal)
    assert result.reason == BboxRefusalReason.MALFORMED_VERTEX
    assert result.span_id == "s1"


def test_get_declaration_bbox_refusal_non_finite_coordinate():
    span = ExtractedSpan(
        span_id="s1",
        text="Net Qty 500g",
        confidence=0.95,
        source_provider=EvidenceProvider.PADDLEOCR,
        region_id="r1",
        polygon=((float("nan"), 10.0), (100.0, 10.0), (100.0, 50.0)),
    )
    field = NormalisedField(
        field_type=DeclarationField.NET_QUANTITY,
        span_refs=("s1",),
        normalised_value="500 g",
        parse_confidence=0.95,
    )
    result = get_declaration_bbox(field, [span])
    assert isinstance(result, BboxRefusal)
    assert result.reason == BboxRefusalReason.NON_FINITE_COORDINATE
    assert result.span_id == "s1"


def test_get_declaration_bbox_refusal_degenerate_geometry():
    span = ExtractedSpan(
        span_id="s1",
        text="Net Qty 500g",
        confidence=0.95,
        source_provider=EvidenceProvider.PADDLEOCR,
        region_id="r1",
        polygon=((10.0, 20.0), (10.0, 20.0), (10.0, 50.0), (10.0, 50.0)),
    )
    field = NormalisedField(
        field_type=DeclarationField.NET_QUANTITY,
        span_refs=("s1",),
        normalised_value="500 g",
        parse_confidence=0.95,
    )
    result = get_declaration_bbox(field, [span])
    assert isinstance(result, BboxRefusal)
    assert result.reason == BboxRefusalReason.DEGENERATE_ENVELOPE
    assert result.span_id is None


def test_get_declaration_bbox_fractional_coordinates():
    span = ExtractedSpan(
        span_id="s1",
        text="Net Qty 500g",
        confidence=0.95,
        source_provider=EvidenceProvider.PADDLEOCR,
        region_id="r1",
        polygon=((10.35, 20.75), (100.25, 20.75), (100.25, 50.85), (10.35, 50.85)),
    )
    field = NormalisedField(
        field_type=DeclarationField.NET_QUANTITY,
        span_refs=("s1",),
        normalised_value="500 g",
        parse_confidence=0.95,
    )
    bbox = get_declaration_bbox(field, [span])
    assert not isinstance(bbox, BboxRefusal)
    assert bbox == (10.35, 20.75, 100.25, 50.85)


# ── Semantic distinction: Category A vs Category B ─────────────────────────


def test_no_span_refs_and_unknown_span_id_have_distinct_reasons():
    """NO_SPAN_REFS and UNKNOWN_SPAN_ID are distinct values — they cannot collapse."""
    field_no_refs = NormalisedField.model_construct(
        field_type=DeclarationField.NET_QUANTITY,
        span_refs=(),
        normalised_value="500 g",
        parse_confidence=0.95,
    )
    field_missing = NormalisedField(
        field_type=DeclarationField.NET_QUANTITY,
        span_refs=("ghost_id",),
        normalised_value="500 g",
        parse_confidence=0.95,
    )
    r1 = get_declaration_bbox(field_no_refs, [])
    r2 = get_declaration_bbox(field_missing, [])
    assert isinstance(r1, BboxRefusal)
    assert isinstance(r2, BboxRefusal)
    assert r1.reason == BboxRefusalReason.NO_SPAN_REFS
    assert r2.reason == BboxRefusalReason.UNKNOWN_SPAN_ID
    assert r1.reason != r2.reason


def test_category_a_and_category_b_produce_distinct_officer_reasons():
    """'Evidence not present' and 'geometry unusable' must not produce the same message."""
    span_good = ExtractedSpan(
        span_id="s1",
        text="Net Qty 500g",
        confidence=0.95,
        source_provider=EvidenceProvider.PADDLEOCR,
        region_id="r1",
        polygon=((10.0, 20.0), (10.0, 20.0), (10.0, 50.0), (10.0, 50.0)),
    )
    field_no_refs = NormalisedField.model_construct(
        field_type=DeclarationField.NET_QUANTITY,
        span_refs=(),
        normalised_value="500 g",
        parse_confidence=0.95,
    )
    field_degenerate = NormalisedField(
        field_type=DeclarationField.NET_QUANTITY,
        span_refs=("s1",),
        normalised_value="500 g",
        parse_confidence=0.95,
    )
    refusal_a = get_declaration_bbox(field_no_refs, [])
    refusal_b = get_declaration_bbox(field_degenerate, [span_good])

    assert isinstance(refusal_a, BboxRefusal)
    assert isinstance(refusal_b, BboxRefusal)
    assert refusal_a.reason != refusal_b.reason
    assert bbox_refusal_officer_reason(refusal_a) != bbox_refusal_officer_reason(refusal_b)


def test_insufficient_vertices_and_malformed_vertex_have_distinct_reasons():
    """A polygon with <3 elements (count defect) vs a polygon with a broken element
    (shape defect) must not collapse to the same reason."""
    # Cause: INSUFFICIENT_VERTICES — polygon exists, count < 3
    span_two_pts = ExtractedSpan.model_construct(
        span_id="s1",
        text="Net Qty 500g",
        confidence=0.95,
        source_provider=EvidenceProvider.PADDLEOCR,
        region_id="r1",
        polygon=((10.0, 20.0), (100.0, 20.0)),
    )
    # Cause: MALFORMED_VERTEX — 3 elements present, but first is a 1-tuple
    span_malformed = ExtractedSpan.model_construct(
        span_id="s2",
        text="Net Qty 500g",
        confidence=0.95,
        source_provider=EvidenceProvider.PADDLEOCR,
        region_id="r1",
        polygon=((10.0,), (100.0, 20.0), (100.0, 50.0)),
    )
    field_s1 = NormalisedField(
        field_type=DeclarationField.NET_QUANTITY,
        span_refs=("s1",),
        normalised_value="500 g",
        parse_confidence=0.95,
    )
    field_s2 = NormalisedField(
        field_type=DeclarationField.NET_QUANTITY,
        span_refs=("s2",),
        normalised_value="500 g",
        parse_confidence=0.95,
    )
    r1 = get_declaration_bbox(field_s1, [span_two_pts])
    r2 = get_declaration_bbox(field_s2, [span_malformed])

    assert isinstance(r1, BboxRefusal)
    assert isinstance(r2, BboxRefusal)
    assert r1.reason == BboxRefusalReason.INSUFFICIENT_VERTICES
    assert r2.reason == BboxRefusalReason.MALFORMED_VERTEX
    assert r1.reason != r2.reason


# ── bbox_refusal_officer_reason — category routing ──────────────────────────


def test_category_a_reasons_produce_evidence_absent_message():
    """Both Category A reasons must say something about evidence, not geometry."""
    for reason in [BboxRefusalReason.NO_SPAN_REFS, BboxRefusalReason.UNKNOWN_SPAN_ID]:
        msg = bbox_refusal_officer_reason(BboxRefusal(reason=reason))
        assert len(msg) > 0
        # Must NOT describe a geometry defect
        assert "polygon" not in msg
        assert "vertex" not in msg
        assert "coordinate" not in msg
        assert "envelope" not in msg


def test_category_b_reasons_produce_geometry_defect_message():
    """All five Category B reasons must describe a geometry defect, not an evidence gap."""
    category_b = [
        BboxRefusalReason.EMPTY_POLYGON,
        BboxRefusalReason.INSUFFICIENT_VERTICES,
        BboxRefusalReason.MALFORMED_VERTEX,
        BboxRefusalReason.NON_FINITE_COORDINATE,
        BboxRefusalReason.DEGENERATE_ENVELOPE,
    ]
    for reason in category_b:
        msg = bbox_refusal_officer_reason(BboxRefusal(reason=reason))
        assert len(msg) > 0


def test_all_seven_reasons_produce_distinct_officer_messages():
    """No two BboxRefusalReason values may produce the same officer-facing string."""
    messages = [bbox_refusal_officer_reason(BboxRefusal(reason=r)) for r in BboxRefusalReason]
    assert len(messages) == len(set(messages)), (
        "Two BboxRefusalReason values produced the same officer message"
    )


# ── span_id traceability ─────────────────────────────────────────────────────


def test_category_b_refusals_carry_span_id():
    """Category B refusals must carry the span_id of the offending span."""
    span = ExtractedSpan.model_construct(
        span_id="offender",
        text="Net Qty 500g",
        confidence=0.95,
        source_provider=EvidenceProvider.PADDLEOCR,
        region_id="r1",
        polygon=((10.0,), (100.0, 20.0), (100.0, 50.0)),  # malformed vertex
    )
    field = NormalisedField(
        field_type=DeclarationField.NET_QUANTITY,
        span_refs=("offender",),
        normalised_value="500 g",
        parse_confidence=0.95,
    )
    result = get_declaration_bbox(field, [span])
    assert isinstance(result, BboxRefusal)
    assert result.span_id == "offender"


def test_category_a_refusals_carry_no_span_id():
    """Category A refusals carry span_id=None — no span was resolved."""
    field = NormalisedField.model_construct(
        field_type=DeclarationField.NET_QUANTITY,
        span_refs=(),
        normalised_value="500 g",
        parse_confidence=0.95,
    )
    result = get_declaration_bbox(field, [])
    assert isinstance(result, BboxRefusal)
    assert result.span_id is None


# ── Success path unchanged ───────────────────────────────────────────────────


def test_valid_bbox_returns_tuple_not_refusal():
    """A valid polygon must return a 4-tuple, never a BboxRefusal."""
    span = ExtractedSpan(
        span_id="s1",
        text="Net Qty 500g",
        confidence=0.95,
        source_provider=EvidenceProvider.PADDLEOCR,
        region_id="r1",
        polygon=((10.0, 20.0), (200.0, 20.0), (200.0, 50.0), (10.0, 50.0)),
    )
    field = NormalisedField(
        field_type=DeclarationField.NET_QUANTITY,
        span_refs=("s1",),
        normalised_value="500 g",
        parse_confidence=0.95,
    )
    result = get_declaration_bbox(field, [span])
    assert not isinstance(result, BboxRefusal)
    assert result == (10.0, 20.0, 200.0, 50.0)


def test_get_declaration_bbox_refuses_hasattr_point_objects():
    """Objects providing .x and .y attributes (duck-typed points) without indexing must be refused.

    `ExtractedSpan.polygon` is typed as tuple[tuple[float, float], ...]. If a malformed
    runtime object with .x / .y attributes reaches get_declaration_bbox, it must NOT
    be duck-typed into coordinates; it must trigger BboxRefusalReason.MALFORMED_VERTEX.
    """

    class PointWithXY:
        def __init__(self, x: float, y: float):
            self.x = x
            self.y = y

    polygon_with_xy_objects = (
        PointWithXY(10.0, 20.0),
        PointWithXY(100.0, 20.0),
        PointWithXY(100.0, 50.0),
        PointWithXY(10.0, 50.0),
    )

    span = ExtractedSpan.model_construct(
        span_id="s1",
        text="Net Qty 500g",
        confidence=0.95,
        source_provider=EvidenceProvider.PADDLEOCR,
        region_id="r1",
        polygon=polygon_with_xy_objects,
    )
    field = NormalisedField(
        field_type=DeclarationField.NET_QUANTITY,
        span_refs=("s1",),
        normalised_value="500 g",
        parse_confidence=0.95,
    )

    result = get_declaration_bbox(field, [span])
    assert isinstance(result, BboxRefusal)
    assert result.reason == BboxRefusalReason.MALFORMED_VERTEX
    assert result.span_id == "s1"
