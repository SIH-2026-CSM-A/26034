"""Tests for Rule 8 — where a declaration appears and the space around it.

Rule 8 is placement. Rule 9 is manner. These tests only touch the first, and
``test_rule8_and_rule9_are_separate_rules`` is here to keep it that way.
"""

from decimal import Decimal

import pytest

from app.modules.rules import (
    FreeSpaceMeasurement,
    Verdict,
    evaluate_rule8_free_space,
    load_rules,
    required_declaration_location,
    rule_by_id,
)


def _measurement(
    *,
    numeral_height: str = "4",
    above: str = "4",
    below: str = "4",
    left: str = "8",
    right: str = "8",
) -> FreeSpaceMeasurement:
    """Return a clearance set that passes unless a caller narrows one side."""
    return FreeSpaceMeasurement(
        numeral_height_mm=Decimal(numeral_height),
        space_above_mm=Decimal(above),
        space_below_mm=Decimal(below),
        space_left_mm=Decimal(left),
        space_right_mm=Decimal(right),
    )


def test_clearance_meeting_the_proviso_passes() -> None:
    """1x the numeral height above and below, 2x left and right, is compliant."""
    evaluation = evaluate_rule8_free_space(_measurement())

    assert evaluation.verdict is Verdict.PASS
    assert evaluation.deficient_sides == ()
    assert evaluation.required_above_below_mm == Decimal("4")
    assert evaluation.required_left_right_mm == Decimal("8")


def test_clearance_exactly_equal_to_the_requirement_passes() -> None:
    """The proviso reads "at least", so the boundary is compliant, not marginal."""
    evaluation = evaluate_rule8_free_space(
        _measurement(numeral_height="2.5", above="2.5", below="2.5", left="5.0", right="5.0")
    )

    assert evaluation.verdict is Verdict.PASS
    assert evaluation.deficient_sides == ()


def test_narrow_horizontal_clearance_is_a_potential_violation() -> None:
    """The left and right requirement is twice the numeral height, not equal to it."""
    evaluation = evaluate_rule8_free_space(_measurement(left="4", right="4"))

    assert evaluation.verdict is Verdict.POTENTIAL_VIOLATION
    assert evaluation.deficient_sides == ("left", "right")
    assert evaluation.required_left_right_mm == Decimal("8")


def test_narrow_vertical_clearance_is_a_potential_violation() -> None:
    """A single deficient side is enough, and it is named rather than counted."""
    evaluation = evaluate_rule8_free_space(_measurement(above="3.9"))

    assert evaluation.verdict is Verdict.POTENTIAL_VIOLATION
    assert evaluation.deficient_sides == ("above",)


@pytest.mark.parametrize("side", ["numeral_height", "above", "below", "left", "right"])
def test_a_missing_or_zero_clearance_fails_to_construct(side: str) -> None:
    """An unmeasured clearance must not evaluate as a pass.

    Zero is the value an absent measurement arrives as. Refusing it at construction is
    why this evaluation never has to guess whether a nil reading means "touching" or
    "we could not measure it" — the two are not the same finding.
    """
    with pytest.raises(ValueError):
        _measurement(**{side: "0"})  # type: ignore[arg-type]


def test_the_multiples_come_from_the_rule_store_not_the_evaluator() -> None:
    """1 and 2 are in the gazette. Nothing may hardcode them in Python."""
    condition = rule_by_id("R8-1-FREE-SPACE").conditions

    assert condition.kind == "free_space"
    assert condition.above_below_multiple_of_numeral_height == Decimal("1")
    assert condition.left_right_multiple_of_numeral_height == Decimal("2")


def test_the_free_space_rule_demands_a_measurement_not_a_text_span() -> None:
    """Rule 8(1)'s proviso is geometrically measurable, so its evidence is a measurement."""
    rule = rule_by_id("R8-1-FREE-SPACE")

    assert "measurement" in rule.evidence_requirement
    assert "span" not in rule.evidence_requirement


def test_placement_requires_the_principal_display_panel() -> None:
    assert required_declaration_location() == "principal_display_panel"


def test_rule8_and_rule9_are_separate_rules() -> None:
    """Placement and manner are distinct obligations and must never merge into one check."""
    by_clause = {rule.clause_ref: rule for rule in load_rules()}

    rule8_kinds = {
        by_clause["Rule 8(1)"].conditions.kind,
        by_clause["Rule 8(1) proviso"].conditions.kind,
    }
    rule9_kinds = {by_clause["Rule 9(1)"].conditions.kind, by_clause["Rule 9(3)"].conditions.kind}

    assert rule8_kinds == {"placement", "free_space"}
    assert rule9_kinds == {"declaration_manner", "outer_container"}
    assert rule8_kinds.isdisjoint(rule9_kinds)
