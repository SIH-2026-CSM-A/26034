"""Tests for Rule 8 — where a declaration appears and the space around it.

Rule 8 is placement. Rule 9 is manner. These tests only touch the first, and
``test_rule8_and_rule9_are_separate_rules`` is here to keep it that way.

Every expected figure below is a literal written in this file. Nothing reads a threshold
out of the rule store and compares it back against the store — that compares the store
with itself and stays green through a same-length corpus edit.
"""

import ast
from decimal import Decimal
from pathlib import Path
from types import ModuleType

import pytest

from app.modules.rules import (
    FreeSpaceCondition,
    FreeSpaceMeasurement,
    SideClearance,
    SideOverlap,
    SideSpace,
    Verdict,
    evaluate_rule8_free_space,
    load_rules,
    required_declaration_location,
    rule_by_id,
)
from app.modules.rules import placement as placement_module
from app.modules.rules import results as results_module

FREE_SPACE_MEASUREMENT_FIELDS = (
    "numeral_height_mm",
    "space_above",
    "space_below",
    "space_left",
    "space_right",
)
"""Every field the Rule 8(1) proviso evaluation may read a figure from.

Written here rather than derived, so a side quietly renamed or a second height quietly
added goes red. ``numeral_height_mm`` is the only height: the proviso scales with the
numeral, and a ``letter_height_mm`` appearing here would be Rule 7's input answering Rule
8's question.
"""

FREE_SPACE_CONDITION_FIELDS = (
    "kind",
    "above_below_multiple_of_numeral_height",
    "left_right_multiple_of_numeral_height",
)
"""Every field of the rule-store condition the evaluator may read a threshold from."""


def _clearance(mm: str) -> SideClearance:
    """Free space of ``mm`` millimetres on one side. ``"0"`` is a flush declaration."""
    return SideClearance(distance_mm=Decimal(mm))


def _overlap(mm: str) -> SideOverlap:
    """Neighbouring ink intruding ``mm`` millimetres into the free space on one side."""
    return SideOverlap(overlap_mm=Decimal(mm))


def _measurement(
    *,
    numeral_height: str = "4",
    above: SideSpace | None = None,
    below: SideSpace | None = None,
    left: SideSpace | None = None,
    right: SideSpace | None = None,
) -> FreeSpaceMeasurement:
    """Return a reading set that passes unless a caller replaces one side."""
    return FreeSpaceMeasurement(
        numeral_height_mm=Decimal(numeral_height),
        space_above=_clearance("4") if above is None else above,
        space_below=_clearance("4") if below is None else below,
        space_left=_clearance("8") if left is None else left,
        space_right=_clearance("8") if right is None else right,
    )


def test_clearance_meeting_the_proviso_passes() -> None:
    """1x the numeral height above and below, 2x left and right, is compliant."""
    evaluation = evaluate_rule8_free_space(_measurement())

    assert evaluation.verdict is Verdict.PASS
    assert evaluation.deficient_sides == ()
    assert evaluation.overlapping_sides == ()
    assert evaluation.required_above_below_mm == Decimal("4")
    assert evaluation.required_left_right_mm == Decimal("8")


def test_clearance_exactly_equal_to_the_requirement_passes() -> None:
    """The proviso reads "at least", so the boundary is compliant, not marginal."""
    evaluation = evaluate_rule8_free_space(
        _measurement(
            numeral_height="2.5",
            above=_clearance("2.5"),
            below=_clearance("2.5"),
            left=_clearance("5.0"),
            right=_clearance("5.0"),
        )
    )

    assert evaluation.verdict is Verdict.PASS
    assert evaluation.deficient_sides == ()


def test_narrow_horizontal_clearance_is_a_potential_violation() -> None:
    """The left and right requirement is twice the numeral height, not equal to it."""
    evaluation = evaluate_rule8_free_space(
        _measurement(left=_clearance("4"), right=_clearance("4"))
    )

    assert evaluation.verdict is Verdict.POTENTIAL_VIOLATION
    assert evaluation.deficient_sides == ("left", "right")
    assert evaluation.overlapping_sides == ()
    assert evaluation.required_left_right_mm == Decimal("8")


def test_narrow_vertical_clearance_is_a_potential_violation() -> None:
    """A single deficient side is enough, and it is named rather than counted."""
    evaluation = evaluate_rule8_free_space(_measurement(above=_clearance("3.9")))

    assert evaluation.verdict is Verdict.POTENTIAL_VIOLATION
    assert evaluation.deficient_sides == ("above",)


def test_a_flush_declaration_is_evaluated_not_rejected() -> None:
    """A declaration touching its neighbour reaches the evaluator and produces a finding.

    Zero is the reading MEA-006 made representable, and it is one of the two readings that
    constitute a breach of the proviso. Typing the side ``gt=0`` rejected it at
    construction, so the one shape the rule exists to catch could not be handed to the rule.
    """
    evaluation = evaluate_rule8_free_space(_measurement(above=_clearance("0")))

    assert evaluation.verdict is Verdict.POTENTIAL_VIOLATION
    assert evaluation.deficient_sides == ("above",)
    assert evaluation.overlapping_sides == ()


def test_an_overlap_is_a_potential_violation_and_is_named_as_one() -> None:
    """Ink crossing into the free space is measured evidence of a breach.

    Not absent evidence: the measurement succeeded and what it found is the intrusion.
    ``overlapping_sides`` reports it apart from a merely narrow side because the two are
    different facts an officer acts on differently.
    """
    evaluation = evaluate_rule8_free_space(_measurement(left=_overlap("2")))

    assert evaluation.verdict is Verdict.POTENTIAL_VIOLATION
    assert evaluation.deficient_sides == ("left",)
    assert evaluation.overlapping_sides == ("left",)


def test_a_large_overlap_is_not_mistaken_for_a_generous_clearance() -> None:
    """An intrusion is never compared against the requirement, whatever it measures.

    10 mm of ink crossing into a side that requires 8 mm of free space is the worst
    reading in this file. Anything that compares the magnitude against the requirement —
    which is what a signed number in one field invites, since 10 > 8 — calls it compliant
    and returns PASS. The evaluator dispatches on which reading arrived instead, so the
    comparison is never reached and the size cannot excuse the intrusion.
    """
    evaluation = evaluate_rule8_free_space(_measurement(numeral_height="4", left=_overlap("10")))

    assert evaluation.verdict is Verdict.POTENTIAL_VIOLATION
    assert evaluation.deficient_sides == ("left",)
    assert evaluation.overlapping_sides == ("left",)


def test_one_physical_fact_has_one_representation() -> None:
    """A flush side is a zero clearance and never a zero overlap, and neither runs backwards.

    Replaces an earlier test asserting that a zero clearance fails to construct. That
    claim was true of the old shape and is false now — MEA-006 settled that a zero margin
    is a physical fact about the package rather than an absent measurement — so the test
    states what is still true instead of being deleted. A zero ``numeral_height_mm`` is
    still no numeral, and remains a construction failure.
    """
    with pytest.raises(ValueError):
        SideOverlap(overlap_mm=Decimal("0"))

    with pytest.raises(ValueError):
        SideClearance(distance_mm=Decimal("-1"))

    with pytest.raises(ValueError):
        _measurement(numeral_height="0")


def test_the_measurement_names_the_numeral_height_and_one_reading_per_side() -> None:
    """Pin the fields a threshold may be derived from, against a tuple written here."""
    assert tuple(FreeSpaceMeasurement.model_fields) == FREE_SPACE_MEASUREMENT_FIELDS
    assert "letter_height_mm" not in FreeSpaceMeasurement.model_fields


def test_the_free_space_condition_names_exactly_two_multiples() -> None:
    """Pin the rule-store fields the evaluator reads its thresholds from."""
    assert tuple(FreeSpaceCondition.model_fields) == FREE_SPACE_CONDITION_FIELDS


def _numeric_literals(module: ModuleType) -> list[str]:
    """Every numeric literal in ``module``'s source, docstrings excluded.

    Resolved through the imported module's own ``__file__`` rather than a path relative to
    this test, which is how a directory scan on this project once resolved to nothing and
    passed by scanning an empty set.

    ``Decimal("4")`` is caught alongside a bare ``4``: the constant is a string to Python
    and a threshold to a reader, and it is the likelier way one would be smuggled in here.

    ``bool`` is excluded because it subclasses ``int``. ``_falls_short`` returns ``True``
    for an overlap and that is a dispatch outcome, not a millimetre — flagging it would
    push the module into contortions to satisfy the test rather than the other way round.
    """
    tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(body, list):
            node.body = [
                child
                for child in body
                if not (
                    isinstance(child, ast.Expr)
                    and isinstance(child.value, ast.Constant)
                    and isinstance(child.value.value, str)
                )
            ]

    numbers = [
        ast.unparse(node)
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, int | float)
        and not isinstance(node.value, bool)
    ]
    decimals = [
        ast.unparse(node)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "Decimal"
        and any(isinstance(arg, ast.Constant) for arg in node.args)
    ]
    return numbers + decimals


@pytest.mark.parametrize("module", [placement_module, results_module])
def test_no_threshold_is_written_into_the_rule8_evaluator_or_its_results(
    module: ModuleType,
) -> None:
    """1 and 2 are in the gazette. Nothing in these two files may spell either.

    The multiples are read from the rule store at evaluation time, so a rule store amended
    tomorrow moves the evaluation without a code change. A figure appearing in Python here
    is that link broken, and it would still produce plausible answers.
    """
    assert _numeric_literals(module) == []


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
