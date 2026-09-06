"""Rule 8 — where a declaration must appear, and the space that must surround it.

Rule 8 governs **placement**. Rule 9 governs **manner**. They are separate rules with
separate evidence and separate consequences, and this module evaluates only the first:
a declaration in the wrong place and a declaration rendered illegibly are two findings,
and merging them would report one where an officer needs both.

Rule 8(1)'s proviso is the geometrically measurable part — clear above and below by at
least the height of the numeral, left and right by at least twice that height — so it is
answered from a calibrated measurement rather than from a text span.
"""

from __future__ import annotations

from decimal import Decimal

from .base import Verdict
from .conditions import FreeSpaceCondition, PlacementCondition
from .evaluator import evaluate_rule
from .loader import rule_by_id
from .results import FreeSpaceMeasurement, Rule8FreeSpaceEvaluation

PDP_PLACEMENT_RULE_ID = "R8-1-PDP-PLACEMENT"
FREE_SPACE_RULE_ID = "R8-1-FREE-SPACE"


def required_declaration_location() -> str:
    """Return the panel Rule 8(1) requires every declaration to appear on."""
    condition = rule_by_id(PDP_PLACEMENT_RULE_ID).conditions
    if not isinstance(condition, PlacementCondition):
        raise TypeError(f"{PDP_PLACEMENT_RULE_ID} does not contain a placement condition")
    return condition.required_location


def _free_space_condition() -> FreeSpaceCondition:
    """Return the Rule 8(1) proviso multiples as the rule store states them."""
    condition = rule_by_id(FREE_SPACE_RULE_ID).conditions
    if not isinstance(condition, FreeSpaceCondition):
        raise TypeError(f"{FREE_SPACE_RULE_ID} does not contain a free-space condition")
    return condition


def evaluate_rule8_free_space(measurement: FreeSpaceMeasurement) -> Rule8FreeSpaceEvaluation:
    """Compare calibrated clearances against the Rule 8(1) proviso requirement.

    The two multiples are read from the rule store, never written here: the figures are
    ``1`` and ``2`` because the gazette says so, and a rule store amended tomorrow moves
    this evaluation without a code change.

    A clearance exactly equal to its requirement passes — the rule reads "at least".
    """
    condition = _free_space_condition()
    numeral_height = measurement.numeral_height_mm
    required_above_below = condition.above_below_multiple_of_numeral_height * numeral_height
    required_left_right = condition.left_right_multiple_of_numeral_height * numeral_height

    deficient = tuple(
        side
        for side, observed, required in (
            ("above", measurement.space_above_mm, required_above_below),
            ("below", measurement.space_below_mm, required_above_below),
            ("left", measurement.space_left_mm, required_left_right),
            ("right", measurement.space_right_mm, required_left_right),
        )
        if observed < required
    )

    proposed = Verdict.POTENTIAL_VIOLATION if deficient else Verdict.PASS
    return Rule8FreeSpaceEvaluation(
        verdict=evaluate_rule(rule_by_id(FREE_SPACE_RULE_ID), proposed),
        required_above_below_mm=Decimal(required_above_below),
        required_left_right_mm=Decimal(required_left_right),
        deficient_sides=deficient,
    )
