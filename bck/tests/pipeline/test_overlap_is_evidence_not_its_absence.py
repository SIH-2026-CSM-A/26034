"""An overlap is evidence of a problem, not the absence of evidence.

INSUFFICIENT_EVIDENCE and FAIL are different findings with different legal consequences:
"we could not read it" against "it is not there". Ink crossing into the free space around a
quantity declaration is the first thing this pipeline can measure that *is* the finding —
the measurement succeeded and what it found is the intrusion — so routing it to
INSUFFICIENT_EVIDENCE would say we obtained nothing about the one reading where we obtained
exactly the thing.

``app.contracts`` states this at the measurement layer: MEA-009 Part A gave an overlap its
own outcome types rather than a :class:`~app.contracts.MeasurementRefusal`. This asserts the
other end of the same claim — that a Rule 8(1) evaluation of one comes out as a finding
about the *package*.

Composition only. Nothing here is wired into the orchestrator: ``measure_margins`` has no
declaration bounding box to measure around until EXT-004, and still reports a negative
clearance as a refusal until MEA-011. This test needs neither, because it puts the two
existing halves together itself.
"""

from decimal import Decimal

from app.contracts import FieldState
from app.modules.rules import (
    FreeSpaceMeasurement,
    SideClearance,
    SideOverlap,
    Verdict,
    evaluate_rule8_free_space,
)
from app.pipeline.dispositions import FIELD_STATE_FROM_VERDICT


def test_an_overlap_becomes_a_finding_about_the_package_not_about_our_reading() -> None:
    """A Rule 8(1) overlap routes to FAIL, and never to INSUFFICIENT_EVIDENCE."""
    evaluation = evaluate_rule8_free_space(
        FreeSpaceMeasurement(
            numeral_height_mm=Decimal("4"),
            space_above=SideClearance(distance_mm=Decimal("4")),
            space_below=SideClearance(distance_mm=Decimal("4")),
            space_left=SideOverlap(overlap_mm=Decimal("2")),
            space_right=SideClearance(distance_mm=Decimal("8")),
        )
    )

    assert evaluation.verdict is Verdict.POTENTIAL_VIOLATION
    assert evaluation.overlapping_sides == ("left",)

    state = FIELD_STATE_FROM_VERDICT[evaluation.verdict]

    assert state is FieldState.FAIL
    assert state is not FieldState.INSUFFICIENT_EVIDENCE
