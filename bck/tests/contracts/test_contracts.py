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
    CategoryProposal,
    DeclarationField,
    EvidenceAssetType,
    EvidenceProvider,
    ExtractedSpan,
    FieldFinding,
    FieldState,
    MeasurementCalibrated,
    MeasurementExact,
    MeasurementMarginCalibrated,
    MeasurementMarginExact,
    MeasurementRefusal,
    MeasurementResult,
    NormalisedField,
    ProductCategory,
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


def test_evidence_asset_type_has_exactly_three_members() -> None:
    """A member ships only alongside something that consumes it.

    The set is what the retention rules distinguish today — a default window, a shorter
    statutory one, and the audit trail that is never purged — not a complete taxonomy of
    evidence. A fourth added here needs a hand-written ``ALTER TYPE ... ADD VALUE``, which
    cannot run in a transaction and which ``alembic check`` reports as clean before failing
    at the first insert, so it is a migration decision and not a local widening.
    """
    assert len(EvidenceAssetType) == 3
    assert set(EvidenceAssetType) == {
        EvidenceAssetType.PRODUCT_IMAGE,
        EvidenceAssetType.PERSONAL_DATA,
        EvidenceAssetType.AUDIT_LOG,
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


def test_exact_mode_carries_the_rule_limb_it_was_computed_under() -> None:
    """Rule 7(4) computes PDP area differently per package form, and the artwork path
    records which limb it used — same field as the calibrated variant."""
    exact = MeasurementExact(value=64.0, unit="cm\u00b2", rule_limb="cylindrical 40%")
    assert exact.rule_limb == "cylindrical 40%"
    assert MeasurementExact(value=2.5, unit="mm").rule_limb is None

    through_union = MEASUREMENT_ADAPTER.validate_python(
        {"mode": "exact", "value": 64.0, "unit": "cm\u00b2", "rule_limb": "rectangular"},
    )
    assert isinstance(through_union, MeasurementExact)
    assert through_union.rule_limb == "rectangular"


def test_a_zero_width_confidence_interval_is_a_valid_measurement() -> None:
    """A zero-variance observation yields an interval of exactly 0.0.

    A uniform text crop against a uniform background has no luminance spread, so the
    interval is genuinely zero. That is a measurement, not a refusal, and rejecting it
    would push a real reading into INSUFFICIENT_EVIDENCE.
    """
    measured = MeasurementCalibrated(
        value=21.0,
        confidence_interval=0.0,
        unit="ratio",
        reference_object="color_variance",
    )
    assert measured.confidence_interval == 0.0


def test_a_negative_confidence_interval_is_still_rejected() -> None:
    """An interval cannot run backwards."""
    with pytest.raises(ValidationError):
        MeasurementCalibrated(
            value=21.0,
            confidence_interval=-0.1,
            unit="ratio",
            reference_object="color_variance",
        )


def test_a_refusal_is_the_only_shape_with_no_value() -> None:
    refusal = MEASUREMENT_ADAPTER.validate_python({"mode": "refusal", "reason": "glare"})
    assert isinstance(refusal, MeasurementRefusal)
    assert not hasattr(refusal, "value")


# --------------------------------------------------------------------------------------
# Margins: the one quantity where zero is a reading, carried by sibling types rather than
# by subclasses that relax what their parent promised.
# --------------------------------------------------------------------------------------


def test_a_margin_of_exactly_zero_is_a_valid_exact_measurement() -> None:
    """A declaration flush against the panel edge has a margin of exactly 0.0."""
    flush = MeasurementMarginExact(value=0.0, unit="mm")
    assert flush.value == 0.0


def test_a_margin_of_exactly_zero_is_a_valid_calibrated_measurement() -> None:
    """The same fact read from a photograph rather than from artwork.

    The interval is non-zero because a margin measured through a reference object may not
    claim one of exactly 0.0 — see
    :func:`test_a_margin_may_not_claim_a_zero_width_confidence_interval`.
    """
    flush = MeasurementMarginCalibrated(
        value=0.0,
        confidence_interval=0.1,
        unit="mm",
        reference_object="coin_10",
    )
    assert flush.value == 0.0


def test_a_non_margin_measurement_of_exactly_zero_is_still_rejected() -> None:
    """The general invariant was not weakened to make room for margins.

    For every quantity but a margin — a letter height, a panel area, a contrast ratio — a
    zero is the detector having found nothing, and reporting it as ``0.0`` would state as
    a measurement what is actually a failure to measure.
    """
    with pytest.raises(ValidationError):
        MeasurementExact(value=0.0, unit="mm")
    with pytest.raises(ValidationError):
        MeasurementCalibrated(
            value=0.0,
            confidence_interval=0.2,
            unit="mm",
            reference_object="coin_10",
        )


def test_a_negative_margin_is_rejected_by_both_margin_shapes() -> None:
    """``ge=0`` admits zero, not the whole negative half-line. Free space cannot run
    backwards any more than an interval can."""
    with pytest.raises(ValidationError):
        MeasurementMarginExact(value=-0.1, unit="mm")
    with pytest.raises(ValidationError):
        MeasurementMarginCalibrated(
            value=-0.1,
            confidence_interval=0.1,
            unit="mm",
            reference_object="coin_10",
        )


def test_a_margin_may_not_claim_a_zero_width_confidence_interval() -> None:
    """Zero value and zero interval are different questions; only the second is barred.

    A margin recovered from a photograph carries pixel quantisation and reference-object
    localisation error, so an interval of exactly 0.0 asserts perfect certainty about a
    physical distance. :class:`MeasurementCalibrated` still permits it, because a
    zero-variance contrast-ratio observation genuinely has no spread.
    """
    with pytest.raises(ValidationError):
        MeasurementMarginCalibrated(
            value=0.0,
            confidence_interval=0.0,
            unit="mm",
            reference_object="coin_10",
        )
    unspread = MeasurementCalibrated(
        value=2.5,
        confidence_interval=0.0,
        unit="ratio",
        reference_object="color_variance",
    )
    assert unspread.confidence_interval == 0.0


def test_a_margin_is_not_an_instance_of_the_measurement_it_relaxes() -> None:
    """The margin shapes are siblings, not subclasses.

    A subclass relaxing ``value`` from ``gt=0`` to ``ge=0`` would leave
    ``isinstance(margin, MeasurementExact)`` answering yes for an object that no longer
    holds what :class:`MeasurementExact` promises, and every ``isinstance`` check written
    against the strict type — several in ``tests/modules/measurement`` — would start
    passing vacuously. This is the assertion that stops that shape being reintroduced.
    """
    margin_exact = MeasurementMarginExact(value=0.0, unit="mm")
    margin_calibrated = MeasurementMarginCalibrated(
        value=0.0,
        confidence_interval=0.1,
        unit="mm",
        reference_object="coin_10",
    )
    assert not isinstance(margin_exact, MeasurementExact)
    assert not isinstance(margin_calibrated, MeasurementCalibrated)

    strict_exact = MeasurementExact(value=2.5, unit="mm")
    strict_calibrated = MeasurementCalibrated(
        value=2.5,
        confidence_interval=0.2,
        unit="mm",
        reference_object="coin_10",
    )
    assert not isinstance(strict_exact, MeasurementMarginExact)
    assert not isinstance(strict_calibrated, MeasurementMarginCalibrated)


def test_each_measurement_shape_round_trips_through_the_union_as_itself() -> None:
    """Five value shapes, five discriminators, no collapsing on the way back.

    ``type(...) is`` rather than ``isinstance``: a subclass would satisfy ``isinstance``
    and defeat the point of
    :func:`test_a_margin_is_not_an_instance_of_the_measurement_it_relaxes`.
    """
    originals = (
        MeasurementExact(value=2.5, unit="mm"),
        MeasurementMarginExact(value=0.0, unit="mm"),
        MeasurementCalibrated(
            value=2.5, confidence_interval=0.2, unit="mm", reference_object="coin_10"
        ),
        MeasurementMarginCalibrated(
            value=0.0, confidence_interval=0.1, unit="mm", reference_object="coin_10"
        ),
        MeasurementRefusal(reason="glare"),
    )
    for original in originals:
        restored = MEASUREMENT_ADAPTER.validate_python(original.model_dump())
        assert type(restored) is type(original), (
            f"{original.mode} came back as {type(restored).__name__}"
        )
        assert restored == original


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
    """Pins the property: an amended rule does not reach a snapshot already taken.

    What this does *not* prove is which line provides that. ``RuleParameterSnapshot``
    annotates ``parameters`` as ``dict[str, JsonValue]``, and validating that annotation
    rebuilds the mapping, so this test passes even with the copy in ``from_rule`` removed
    entirely. It goes red only if the isolation is lost in a way the type no longer
    covers — see :func:`test_nested_rule_parameters_are_snapshotted_by_value` for the
    mutation that demonstrates it failing.
    """
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


def test_nested_rule_parameters_are_snapshotted_by_value() -> None:
    """The same guarantee one level down: a band table amended in place stays out.

    Rule parameters are not flat. A quantity band table is a list of dicts and a format
    rule is a dict of lists, and an amendment edits those in place as readily as it
    replaces the mapping. A snapshot that shared them would re-adjudicate a months-old
    verdict the moment the rule was amended.

    **What this test does not prove.** It cannot fail against the annotation as it stands.
    ``parameters`` is ``dict[str, JsonValue]``, and validating that walks the mapping and
    rebuilds every container in it, so the snapshot is isolated with or without the
    ``deepcopy`` in :meth:`RuleParameterSnapshot.from_rule` — it passes with the copy
    removed altogether. It was confirmed to go red by widening the field to
    ``dict[str, Any]``, where pydantic passes nested containers through by identity and
    the copy becomes the only guard. That is what this test pins: the day someone widens
    that annotation, the ``deepcopy`` has to still be there or this goes red.
    """
    rule = _rule(
        parameters={
            "quantity_bands": [{"upto_g": 50, "height_mm": 1}],
            "permitted_formats": {"date_of_manufacture": ["MM/YYYY"]},
        }
    )
    record = _verdict_record_from(rule)

    rule.parameters["quantity_bands"].append({"upto_g": 200, "height_mm": 2})
    rule.parameters["quantity_bands"][0]["height_mm"] = 99
    rule.parameters["permitted_formats"]["date_of_manufacture"].append("DD/MM/YYYY")

    assert record.findings[0].rule_snapshot.parameters == {
        "quantity_bands": [{"upto_g": 50, "height_mm": 1}],
        "permitted_formats": {"date_of_manufacture": ["MM/YYYY"]},
    }


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


def test_product_category_has_exactly_three_members() -> None:
    assert len(ProductCategory) == 3, (
        "A member of ProductCategory is a routing target, not a label. Adding one "
        "without the gazette provision that routes an obligation away from these Rules "
        "gives the sector dispatch a category it will match no rule for."
    )
    assert set(ProductCategory) == {
        ProductCategory.FOOD,
        ProductCategory.COSMETICS,
        ProductCategory.MEDICAL_DEVICE,
    }


def test_product_category_values_match_the_rule_store_sector_keys() -> None:
    """The one property the move could have broken silently.

    ``sector_overrides`` matches these values against the ``sector:`` keys in the rule
    store. Upper-casing them to match every other vocabulary in this package would leave
    every type check passing and every sector override matching nothing — a medical
    device evaluated against Rule 7 Table-I, which G.S.R. 778(E) disapplies.
    """
    assert {category.value for category in ProductCategory} == {
        "food",
        "cosmetics",
        "medical_device",
    }


def test_the_rules_module_and_contracts_share_one_product_category() -> None:
    """Re-export, not a copy.

    ``rules/base.py`` names this type so its four internal importers keep working, but a
    second class with the same members would let the two drift: a category confirmed
    against one would route to nothing through the other. Identity, not equality —
    equality is what a copy would also satisfy.
    """
    from app.modules.rules import ProductCategory as RulesProductCategory

    assert RulesProductCategory is ProductCategory


def test_a_category_proposal_must_cite_at_least_one_span() -> None:
    """An evidence-free proposal is unconstructible, not discouraged."""
    with pytest.raises(ValidationError):
        CategoryProposal(
            category=ProductCategory.FOOD,
            confidence=0.91,
            span_refs=(),
            reason="the panel declares a nutritional information table",
        )


def test_a_category_proposal_must_say_why() -> None:
    with pytest.raises(ValidationError):
        CategoryProposal(
            category=ProductCategory.FOOD,
            confidence=0.91,
            span_refs=("span-1",),
            reason="",
        )


def test_a_category_proposal_confidence_stays_within_zero_and_one() -> None:
    for confidence in (-0.1, 1.1):
        with pytest.raises(ValidationError):
            CategoryProposal(
                category=ProductCategory.MEDICAL_DEVICE,
                confidence=confidence,
                span_refs=("span-1",),
                reason="the package bears a CDSCO import licence number",
            )


def test_a_category_proposal_carries_its_evidence() -> None:
    proposal = CategoryProposal(
        category=ProductCategory.COSMETICS,
        confidence=0.74,
        span_refs=("span-2", "span-5"),
        reason="the panel bears a shelf-life declaration in the cosmetics form",
    )
    assert proposal.span_refs == ("span-2", "span-5")
    assert proposal.category is ProductCategory.COSMETICS


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
