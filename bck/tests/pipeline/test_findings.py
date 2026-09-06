"""What the pipeline may and may not conclude from the evidence it has.

Every test here is falsifiable and was made to fail before it was claimed. Four of them
guard the constraints that would be liabilities rather than bugs if they broke: a
millimetre figure invented from an uncalibrated photograph, INSUFFICIENT_EVIDENCE
collapsing into FAIL, an obligation evaluated under rules that do not govern the package,
and a verdict outside the three the system is allowed to reach.
"""

import re
from datetime import UTC, date, datetime
from typing import get_args

import pytest

from app.contracts import (
    FieldState,
    MeasurementCalibrated,
    MeasurementRefusal,
    Verdict,
)
from app.modules.rules import (
    ProductCategory,
    default_rule_set_version,
    load_rules,
)
from app.modules.rules import Verdict as RuleVerdict
from app.modules.rules.conditions import RuleCondition, SectorOverrideCondition
from app.pipeline.dispositions import (
    CONDITION_DISPOSITION,
    FIELD_STATE_FROM_VERDICT,
    SECTOR_GOVERNED_RULES,
)
from app.pipeline.findings import build_findings
from app.pipeline.rule_findings import EvidenceContext
from app.pipeline.verdict import assemble_verdict

from .sector_gate import findings_for_rule

EVALUATION_DATE = date(2026, 9, 6)
NO_CALIBRATION = MeasurementRefusal(reason="no reference object was in frame")
UNREADABLE = "the panel was read but no declaration was bound to a span."

MILLIMETRE = re.compile(r"\d+(?:[.,]\d+)?\s*(?:mm|millimetres?|millimeters?)\b", re.IGNORECASE)
"""A number presented as a length in millimetres.

Matches a *figure*, not the letters "mm": ``normal_minimum_height_mm`` is a field name in a
quoted gazette table and is not a claim about this package.
"""


def context(**overrides: object) -> EvidenceContext:
    """An uncalibrated image scan of a package whose category nobody has confirmed."""
    fields: dict[str, object] = {
        "rule_set_version": default_rule_set_version(),
        "evaluation_date": EVALUATION_DATE,
        "declared": {},
        "measurements": dict.fromkeys(
            ("table_height", "width_ratio", "free_space", "pdp_area"), NO_CALIBRATION
        ),
        "product_category": None,
        "source_is_listing": False,
        "unreadable_reason": UNREADABLE,
    }
    fields.update(overrides)
    return EvidenceContext(**fields)  # type: ignore[arg-type]


def findings_for(**overrides: object):
    return build_findings(load_rules(), context(**overrides))


def test_every_condition_kind_has_a_disposition() -> None:
    """A condition variant added to the rule store must state what this pipeline does.

    Without this, a new ``RuleCondition`` variant produces no finding for every rule that
    uses it, and a dropped finding reads downstream as a package with nothing wrong.
    """
    variants = get_args(get_args(RuleCondition)[0])
    encoded = {get_args(v.model_fields["kind"].annotation)[0] for v in variants}
    assert encoded == set(CONDITION_DISPOSITION), (
        "app.modules.rules.conditions and CONDITION_DISPOSITION disagree. A condition "
        "with no disposition produces no finding for every rule that carries it."
    )


def test_every_sector_override_target_gates_a_rule() -> None:
    """Every target a sector override names must have a packaged rule held back for it.

    An override that redirects an obligation nothing is mapped to would route nothing:
    the carve-out would be recorded in the store and have no effect on any finding.
    """
    named = {
        target
        for rule in load_rules()
        if isinstance(rule.conditions, SectorOverrideCondition)
        for target in rule.conditions.overrides
    }
    assert named <= set(SECTOR_GOVERNED_RULES.values()), (
        f"sector overrides name {named - set(SECTOR_GOVERNED_RULES.values())}, which gate "
        f"no rule in SECTOR_GOVERNED_RULES"
    )


def test_every_rules_verdict_member_is_mapped_to_a_field_state() -> None:
    """A new ``rules.Verdict`` member must not become a KeyError on a real scan."""
    assert set(FIELD_STATE_FROM_VERDICT) == set(RuleVerdict), (
        "rules.Verdict has a member with no per-field state. The alternative to this "
        "test is a KeyError surfacing at verdict assembly on a real scan."
    )


def test_insufficient_evidence_is_never_mapped_from_an_evaluator() -> None:
    """The two states that mean "we did not evaluate" have no source verdict.

    They are reached by not evaluating a rule. A mapping that produced either of them
    from an evaluator's answer would be one edit from producing FAIL instead.
    """
    assert FieldState.INSUFFICIENT_EVIDENCE not in FIELD_STATE_FROM_VERDICT.values()
    assert FieldState.NOT_APPLICABLE not in FIELD_STATE_FROM_VERDICT.values()


def test_an_uncalibrated_scan_refuses_every_letter_height_field() -> None:
    """No reference object means no measurement, and no measurement means no conclusion.

    INSUFFICIENT_EVIDENCE and never FAIL: the package may well comply, and we did not
    obtain the evidence to say either way.

    Food is confirmed so that Rule 7 is actually evaluated. This test previously ran with
    no category and accepted *either* the measurement reason or the sector gate's, which
    meant it passed without the measurement path running at all — the guard in
    ``sector_gate`` is what surfaced that, and the reason assertion is now specific.
    """
    measured = findings_for_rule(
        findings_for(product_category=ProductCategory.FOOD), "R7-2-TABLE-I"
    )
    assert measured, "Rule 7 Table-I produced no finding at all"
    assert {f.state for f in measured} == {FieldState.INSUFFICIENT_EVIDENCE}
    assert all("the measurement this rule needs was not made" in f.reason for f in measured)


def test_an_uncalibrated_response_states_no_millimetre_it_claims_to_have_measured() -> None:
    """Grep the serialised response for a measured length. There must not be one.

    **Requirements may carry millimetres; observations may not.** ``expected_value`` quotes
    what a rule requires and ``rule_snapshot`` quotes the gazette, so both legitimately
    carry the figures the Rules state — redacting them would break the guarantee that a
    verdict can be re-derived from itself. ``observed_value`` and ``reason`` describe what
    *we saw*, and from an uncalibrated photograph we saw no length at all.

    ``reason`` is the falsifiable one: it is free text written by whichever stage produced
    the finding, so it is where a leak would actually happen.

    The category is confirmed as food deliberately. Food carves nothing out of Rule 7, so
    Table-I is actually *evaluated* and the measurement stage really runs — with an
    unconfirmed category the sector gate settles the rule first and this test would never
    reach the code it is guarding.
    """
    record = assemble_verdict(
        subject_ref="scan-uncalibrated",
        findings=findings_for(product_category=ProductCategory.FOOD),
        rule_set_version=default_rule_set_version(),
        evaluated_at=datetime.now(UTC),
    )
    leaked = [
        (f.field.value, name, value)
        for f in record.findings
        for name in ("observed_value", "reason")
        if (value := getattr(f, name)) and MILLIMETRE.search(value)
    ]
    assert leaked == [], f"a measured millimetre figure reached the officer: {leaked}"


def test_an_unconfirmed_category_never_produces_a_fail() -> None:
    """Sector-dependent obligations wait for a confirmed category. They do not fail.

    A sector override is a carve-out: until somebody confirms what the product is, we do
    not know whether the packaged rules govern the obligation at all, so asserting a
    shortfall under them would be asserting it under a provision that may not apply.

    Run against a listing that declares nothing, so that *without* the gate every one of
    these rules would reach FAIL — an absent declaration the pipeline looked for is a
    finding about the listing. On the image path the EXT-004 reason would produce
    INSUFFICIENT_EVIDENCE anyway and the gate could be deleted without this noticing.
    """
    gated = [
        f
        for f in findings_for(source_is_listing=True, unreadable_reason=None, measurements={})
        if f.rule_snapshot.rule_id in SECTOR_GOVERNED_RULES
    ]
    assert gated, "no sector-gated rule produced a finding"
    assert FieldState.FAIL not in {f.state for f in gated}
    assert {f.state for f in gated} == {FieldState.INSUFFICIENT_EVIDENCE}


def test_a_confirmed_sector_routes_its_obligations_out_of_the_packaged_rules() -> None:
    """A medical device carves out of Table-I rather than being judged more strictly."""
    routed = findings_for_rule(
        findings_for(product_category=ProductCategory.MEDICAL_DEVICE), "R7-2-TABLE-I"
    )
    assert {f.state for f in routed} == {FieldState.NOT_APPLICABLE}
    assert all("Medical Devices" in f.reason for f in routed)


def test_a_confirmed_category_does_not_carve_out_an_unrelated_sector() -> None:
    """Confirming *food* must not route a medical-device obligation.

    Guards the dispatch itself: a lookup keyed on the wrong thing would carve out
    everything for anybody who confirmed anything.
    """
    states = {
        f.state
        for f in findings_for_rule(
            findings_for(product_category=ProductCategory.FOOD), "R7-2-TABLE-I"
        )
    }
    assert FieldState.NOT_APPLICABLE not in states


@pytest.mark.parametrize("category", [None, ProductCategory.FOOD, ProductCategory.MEDICAL_DEVICE])
def test_no_code_path_emits_a_verdict_outside_the_three(category) -> None:
    """The verdict is PASS, REVIEW or POTENTIAL_VIOLATION, and there is no fourth."""
    record = assemble_verdict(
        subject_ref="scan-vocabulary",
        findings=findings_for(product_category=category),
        rule_set_version=default_rule_set_version(),
        evaluated_at=datetime.now(UTC),
    )
    assert record.verdict in set(Verdict)
    assert {member.value for member in Verdict} == {"PASS", "REVIEW", "POTENTIAL_VIOLATION"}


def test_a_calibrated_measurement_is_compared_rather_than_refused() -> None:
    """With a real basis the rule is actually evaluated, and states its requirement.

    The counterpart to the refusal tests: if every path returned INSUFFICIENT_EVIDENCE the
    suite above would pass against a pipeline that never measures anything.
    """
    calibrated = {
        "table_height": MeasurementCalibrated(
            value=2.0, confidence_interval=0.1, unit="mm", reference_object="10-rupee coin"
        ),
        "pdp_area": MeasurementCalibrated(
            value=60.0, confidence_interval=1.0, unit="cm2", reference_object="10-rupee coin"
        ),
    }
    findings = findings_for_rule(
        findings_for(measurements=calibrated, product_category=ProductCategory.FOOD),
        "R7-2-TABLE-I",
    )
    assert findings, "Table-I produced no finding with a calibrated measurement"
    assert {f.state for f in findings} <= {FieldState.PASS, FieldState.FAIL}
    assert all(f.expected_value and "mm" in f.expected_value for f in findings)
    assert all(f.observed_value == "2.0 mm" for f in findings)


def test_a_declaration_absent_from_a_listing_is_a_finding_about_the_listing() -> None:
    """With no ``unreadable_reason`` an absence is FAIL, not INSUFFICIENT_EVIDENCE.

    The other half of the distinction: the states are chosen by different inputs, so a
    test that only ever saw INSUFFICIENT_EVIDENCE would not show they were distinguished.
    """
    findings = findings_for(source_is_listing=True, unreadable_reason=None, measurements={})
    absent = findings_for_rule(findings, "R6-1-C")
    assert {f.state for f in absent} == {FieldState.FAIL}
    assert all("looked for and is not present" in f.reason for f in absent)
