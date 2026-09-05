"""Contract guarantees, written as the properties nine other tickets rely on.

Each test here corresponds to a promise `app.contracts` makes to its consumers. They are
deliberately about invariants rather than about individual field spellings: a test that
only checks the five expected names still passes when a sixth is added.
"""

import ast
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import TypeAdapter, ValidationError

from app.contracts import (
    CatalogueRecord,
    DeclarationField,
    EvidenceProvider,
    ExtractedSpan,
    FieldFinding,
    FieldState,
    MeasurementCalibrated,
    MeasurementExact,
    MeasurementRefusal,
    MeasurementResult,
    NormalisedField,
    RuleDefinition,
    RuleParameterSnapshot,
    RuleSetVersion,
    RuleSeverity,
    RuleStatus,
    ToleranceBasis,
    Verdict,
    VerdictRecord,
)

CONTRACTS_DIR = Path(__file__).resolve().parents[2] / "app" / "contracts"

MEASUREMENT_ADAPTER: TypeAdapter[MeasurementResult] = TypeAdapter(MeasurementResult)


def _rule(**overrides: object) -> RuleDefinition:
    """A minimal valid rule. Every test that needs one starts here and overrides."""
    fields: dict[str, object] = {
        "rule_id": "R6-1-e-declared",
        "clause_ref": "6(1)(e)",
        "gazette_ref": "LMPC-2011__amended-to-2021-10-31__maharashtra-compilation.pdf",
        "source_text": "the retail sale price of the package;",
        "status": RuleStatus.VERIFIED,
        "effective_from": date(2011, 4, 1),
        "severity": RuleSeverity.MANDATORY,
    }
    fields.update(overrides)
    return RuleDefinition(**fields)  # type: ignore[arg-type]


# --------------------------------------------------------------------------------------
# Enum cardinality. Count assertions, so a member added later fails even when every
# original member is still present.
# --------------------------------------------------------------------------------------


def test_field_state_has_exactly_five_members() -> None:
    assert len(FieldState) == 5, (
        "FieldState is a fixed five-state vocabulary. Adding a sixth changes the meaning "
        "of every stored finding — raise it as a contracts change, not a local widening."
    )
    assert set(FieldState) == {
        FieldState.PASS,
        FieldState.FAIL,
        FieldState.REVIEW_REQUIRED,
        FieldState.NOT_APPLICABLE,
        FieldState.INSUFFICIENT_EVIDENCE,
    }


def test_insufficient_evidence_is_distinct_from_fail() -> None:
    """The distinction the five-state vocabulary exists for."""
    assert FieldState.INSUFFICIENT_EVIDENCE is not FieldState.FAIL
    assert FieldState.INSUFFICIENT_EVIDENCE != FieldState.FAIL


def test_verdict_has_exactly_three_members() -> None:
    assert len(Verdict) == 3, (
        "Verdict is PASS / REVIEW / POTENTIAL_VIOLATION. There is no member for a "
        "confirmed breach: the system recommends and a human confirms."
    )
    assert set(Verdict) == {Verdict.PASS, Verdict.REVIEW, Verdict.POTENTIAL_VIOLATION}


def test_no_verdict_member_asserts_a_confirmed_violation() -> None:
    forbidden = {"violation_confirmed", "confirmed", "non_compliant", "noncompliant", "guilty"}
    assert {member.name.lower() for member in Verdict}.isdisjoint(forbidden)


# --------------------------------------------------------------------------------------
# Every enum member states its legal or operational meaning.
#
# Python discards member docstrings at runtime — `FieldState.PASS.__doc__` returns the
# class docstring — so this reads the source rather than the objects.
# --------------------------------------------------------------------------------------


def _members_missing_docstrings(source: Path) -> list[str]:
    tree = ast.parse(source.read_text(encoding="utf-8"))
    missing: list[str] = []
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        body = node.body
        for index, statement in enumerate(body):
            if not isinstance(statement, ast.Assign):
                continue
            following = body[index + 1] if index + 1 < len(body) else None
            documented = (
                isinstance(following, ast.Expr)
                and isinstance(following.value, ast.Constant)
                and isinstance(following.value.value, str)
            )
            if not documented:
                names = [t.id for t in statement.targets if isinstance(t, ast.Name)]
                missing.extend(f"{node.name}.{name}" for name in names)
    return missing


def test_every_enum_member_documents_its_meaning() -> None:
    missing = _members_missing_docstrings(CONTRACTS_DIR / "enums.py")
    assert not missing, (
        f"enum members with no docstring: {missing}. An officer acts on these values and "
        "an evidence export reproduces them; each one states what it means in law or in "
        "the workflow."
    )


# --------------------------------------------------------------------------------------
# Measurement: no millimetre value without the exact-artwork mode or a calibration source.
# --------------------------------------------------------------------------------------


def test_calibrated_millimetres_without_a_reference_object_raises() -> None:
    with pytest.raises(ValidationError):
        MeasurementCalibrated(value=2.5, confidence_interval=0.2, unit="mm")


def test_calibrated_millimetres_without_a_confidence_interval_raises() -> None:
    with pytest.raises(ValidationError):
        MeasurementCalibrated(value=2.5, unit="mm", reference_object="coin_10")


def test_millimetre_payload_with_no_calibration_source_is_rejected_by_the_union() -> None:
    with pytest.raises(ValidationError):
        MEASUREMENT_ADAPTER.validate_python({"mode": "calibrated", "value": 2.5, "unit": "mm"})


def test_millimetre_payload_with_no_mode_matches_no_variant() -> None:
    """There is no fourth shape. A bare value and unit is not a measurement."""
    with pytest.raises(ValidationError):
        MEASUREMENT_ADAPTER.validate_python({"value": 2.5, "unit": "mm"})


def test_a_refusal_cannot_carry_a_value() -> None:
    with pytest.raises(ValidationError):
        MeasurementRefusal(reason="no reference object in frame", value=2.5)


def test_the_two_permitted_millimetre_shapes_construct() -> None:
    exact = MEASUREMENT_ADAPTER.validate_python(
        {"mode": "exact", "value": 2.5, "unit": "mm"},
    )
    calibrated = MEASUREMENT_ADAPTER.validate_python(
        {
            "mode": "calibrated",
            "value": 2.5,
            "confidence_interval": 0.2,
            "unit": "mm",
            "reference_object": "coin_10",
        },
    )
    assert isinstance(exact, MeasurementExact)
    assert isinstance(calibrated, MeasurementCalibrated)
    assert calibrated.reference_object == "coin_10"


def test_a_refusal_is_the_only_shape_with_no_value() -> None:
    refusal = MEASUREMENT_ADAPTER.validate_python({"mode": "refusal", "reason": "glare"})
    assert isinstance(refusal, MeasurementRefusal)
    assert not hasattr(refusal, "value")


# --------------------------------------------------------------------------------------
# Rules: sourcing, and the two separate numeric fields.
# --------------------------------------------------------------------------------------


def test_a_rule_with_no_gazette_ref_raises_on_construction() -> None:
    with pytest.raises(ValidationError):
        _rule(gazette_ref=None)


def test_a_rule_with_a_blank_gazette_ref_raises_on_construction() -> None:
    with pytest.raises(ValidationError):
        _rule(gazette_ref="")


def test_rounding_increment_and_tolerance_are_two_independent_fields() -> None:
    """They diverge at the boundary, so the schema has to hold both separately.

    With an increment of 0.05 a declared 1.02 is not expressed in permitted steps; with
    a tolerance of 0.01 against a required 1.00 it is outside the permitted difference.
    One number cannot answer both questions.
    """
    rule = _rule(
        rounding_increment=Decimal("0.05"),
        tolerance=Decimal("0.01"),
        tolerance_basis=ToleranceBasis.ABSOLUTE,
    )
    assert rule.rounding_increment == Decimal("0.05")
    assert rule.tolerance == Decimal("0.01")
    assert rule.rounding_increment != rule.tolerance
    assert rule.tolerance_basis is ToleranceBasis.ABSOLUTE


def test_a_rule_may_have_a_rounding_increment_and_no_tolerance() -> None:
    rule = _rule(rounding_increment=Decimal("0.05"))
    assert rule.rounding_increment == Decimal("0.05")
    assert rule.tolerance is None


def test_a_tolerance_without_a_basis_raises() -> None:
    """0.05 is five paise or five percent. Unbasised, it is neither."""
    with pytest.raises(ValidationError):
        _rule(tolerance=Decimal("0.05"))


def test_a_percentage_tolerance_is_distinguishable_from_an_absolute_one() -> None:
    percentage = _rule(tolerance=Decimal("2"), tolerance_basis=ToleranceBasis.PERCENTAGE)
    absolute = _rule(tolerance=Decimal("2"), tolerance_basis=ToleranceBasis.ABSOLUTE)
    assert percentage.tolerance == absolute.tolerance
    assert percentage.tolerance_basis is not absolute.tolerance_basis


def test_a_format_rule_carries_neither_field() -> None:
    """Rule 6(11) prescribes a unit basis and states no tolerance and no increment."""
    rule = _rule(rule_id="R6-11-basis", clause_ref="6(11)", source_text="unit sale price")
    assert rule.rounding_increment is None
    assert rule.tolerance is None


def test_rule_applicability_is_resolved_against_a_given_date() -> None:
    not_yet = _rule(effective_from=date(2027, 7, 1))
    assert not not_yet.in_force_on(date(2026, 9, 5))
    assert not_yet.in_force_on(date(2027, 7, 1))


def test_a_rule_set_rejects_duplicate_rule_ids() -> None:
    with pytest.raises(ValidationError):
        RuleSetVersion(
            version="2026.09.1",
            published_at=datetime(2026, 9, 5, tzinfo=UTC),
            rules=(_rule(), _rule()),
        )


# --------------------------------------------------------------------------------------
# Verdict records carry rule parameters by value, never by reference.
# --------------------------------------------------------------------------------------


def _verdict_record_from(rule: RuleDefinition) -> VerdictRecord:
    return VerdictRecord(
        subject_ref="scan-0001",
        verdict=Verdict.POTENTIAL_VIOLATION,
        rule_set_version="2026.09.1",
        evaluated_at=datetime(2026, 9, 5, 10, 30, tzinfo=UTC),
        findings=(
            FieldFinding(
                field=DeclarationField.RETAIL_SALE_PRICE,
                state=FieldState.FAIL,
                rule_snapshot=RuleParameterSnapshot.from_rule(rule, "2026.09.1"),
                observed_value="45",
                expected_value="MRP Rs. 45.00 inclusive of all taxes",
                reason="Declared price omits the inclusive-of-all-taxes wording.",
                evidence_span_ids=("span-7",),
            ),
        ),
        field_providers={DeclarationField.RETAIL_SALE_PRICE: EvidenceProvider.TESSERACT},
    )


def test_a_verdict_record_holds_no_reference_to_a_rules_table() -> None:
    record = _verdict_record_from(_rule())
    reference_shaped = {"rule_definition_id", "rule_set_id", "rule_fk", "rule_ref"}
    assert set(VerdictRecord.model_fields).isdisjoint(reference_shaped)
    assert set(FieldFinding.model_fields).isdisjoint(reference_shaped)
    assert record.findings[0].rule_snapshot.gazette_ref


def test_rule_parameter_values_are_present_directly_on_the_record() -> None:
    rule = _rule(
        tolerance=Decimal("2"),
        tolerance_basis=ToleranceBasis.PERCENTAGE,
        parameters={"required_wording": "inclusive of all taxes"},
    )
    snapshot = _verdict_record_from(rule).findings[0].rule_snapshot

    assert snapshot.clause_ref == "6(1)(e)"
    assert snapshot.gazette_ref == rule.gazette_ref
    assert snapshot.source_text == rule.source_text
    assert snapshot.tolerance == Decimal("2")
    assert snapshot.tolerance_basis is ToleranceBasis.PERCENTAGE
    assert snapshot.parameters == {"required_wording": "inclusive of all taxes"}
    assert snapshot.rule_set_version == "2026.09.1"


def test_amending_the_rule_afterwards_does_not_re_adjudicate_the_record() -> None:
    """The failure this modelling decision exists to prevent."""
    rule = _rule(
        tolerance=Decimal("2"),
        tolerance_basis=ToleranceBasis.PERCENTAGE,
        parameters={"required_wording": "inclusive of all taxes"},
    )
    record = _verdict_record_from(rule)

    amended = rule.model_copy(
        update={
            "tolerance": Decimal("5"),
            "source_text": "amended text",
            "parameters": {"required_wording": "something else"},
        }
    )
    rule.parameters["required_wording"] = "mutated in place"

    snapshot = record.findings[0].rule_snapshot
    assert amended.tolerance == Decimal("5")
    assert snapshot.tolerance == Decimal("2")
    assert snapshot.source_text == "the retail sale price of the package;"
    assert snapshot.parameters == {"required_wording": "inclusive of all taxes"}


def test_a_verdict_record_names_the_provider_behind_each_field() -> None:
    record = _verdict_record_from(_rule())
    assert record.field_providers[DeclarationField.RETAIL_SALE_PRICE] is EvidenceProvider.TESSERACT


def test_a_verdict_record_rejects_a_verdict_with_no_findings_behind_it() -> None:
    with pytest.raises(ValidationError):
        VerdictRecord(
            subject_ref="scan-0002",
            verdict=Verdict.PASS,
            rule_set_version="2026.09.1",
            evaluated_at=datetime(2026, 9, 5, tzinfo=UTC),
            findings=(),
        )


# --------------------------------------------------------------------------------------
# Evidence shapes.
# --------------------------------------------------------------------------------------


def test_a_span_records_which_provider_read_it() -> None:
    span = ExtractedSpan(
        span_id="span-7",
        text="MRP Rs. 45",
        polygon=((10.0, 20.0), (90.0, 20.0), (90.0, 40.0), (10.0, 40.0)),
        confidence=0.93,
        source_provider=EvidenceProvider.PADDLEOCR,
        region_id="pdp-front",
    )
    assert span.source_provider is EvidenceProvider.PADDLEOCR
    assert len(span.polygon) == 4


def test_a_span_polygon_needs_at_least_three_vertices() -> None:
    with pytest.raises(ValidationError):
        ExtractedSpan(
            span_id="span-8",
            text="45",
            polygon=((10.0, 20.0), (90.0, 20.0)),
            confidence=0.9,
            source_provider=EvidenceProvider.PADDLEOCR,
            region_id="pdp-front",
        )


def test_an_unknown_provider_is_rejected_rather_than_recorded() -> None:
    with pytest.raises(ValidationError):
        ExtractedSpan(
            span_id="span-9",
            text="45",
            polygon=((0.0, 0.0), (1.0, 0.0), (1.0, 1.0)),
            confidence=0.9,
            source_provider="paddle",
            region_id="pdp-front",
        )


def test_a_normalised_field_can_cite_every_span_it_was_built_from() -> None:
    """An address runs over several lines and is read as several spans."""
    field = NormalisedField(
        field_type=DeclarationField.NAME_AND_ADDRESS,
        span_refs=("span-1", "span-2", "span-3"),
        normalised_value="SATVIK FOODS PVT LTD, PUNE, 411001",
        parse_confidence=0.88,
    )
    assert field.span_refs == ("span-1", "span-2", "span-3")
    assert field.numeric_value is None


def test_a_normalised_field_keeps_its_numeric_value_exact() -> None:
    field = NormalisedField(
        field_type=DeclarationField.NET_QUANTITY,
        span_refs=("span-4",),
        normalised_value="45.50",
        numeric_value=Decimal("45.50"),
        unit="g",
        parse_confidence=0.96,
    )
    assert field.numeric_value == Decimal("45.50")
    assert field.numeric_value * 3 == Decimal("136.50")


def test_a_normalised_field_must_cite_at_least_one_span() -> None:
    with pytest.raises(ValidationError):
        NormalisedField(
            field_type=DeclarationField.NET_QUANTITY,
            span_refs=(),
            normalised_value="45",
            parse_confidence=0.9,
        )


def test_declaration_fields_cover_the_rule_6_obligations() -> None:
    assert len(DeclarationField) == 11
    assert DeclarationField.NAME_AND_ADDRESS in DeclarationField
    assert DeclarationField.UNIT_SALE_PRICE in DeclarationField


def test_a_catalogue_record_is_a_first_class_ingestion_input() -> None:
    record = CatalogueRecord(
        listing_id="L-4471",
        platform="example-marketplace",
        retrieved_at=datetime(2026, 9, 5, tzinfo=UTC),
        title="Satvik Foods Turmeric Powder 100 g",
        declared_fields={
            DeclarationField.NET_QUANTITY: "100 g",
            DeclarationField.RETAIL_SALE_PRICE: "MRP Rs. 45.00 inclusive of all taxes",
        },
        seller_name="Example Retail",
    )
    assert DeclarationField.COUNTRY_OF_ORIGIN not in record.declared_fields
    assert record.declared_fields[DeclarationField.NET_QUANTITY] == "100 g"


# --------------------------------------------------------------------------------------
# Contract-wide model policy.
# --------------------------------------------------------------------------------------


def test_contract_models_reject_fields_they_do_not_know() -> None:
    with pytest.raises(ValidationError):
        _rule(gazzette_ref="typo")


def test_contract_models_are_immutable_once_built() -> None:
    record = _verdict_record_from(_rule())
    with pytest.raises(ValidationError):
        record.verdict = Verdict.PASS  # type: ignore[misc]
