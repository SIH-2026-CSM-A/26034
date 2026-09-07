"""Return shapes for the deterministic rule evaluations in this module.

Kept apart from :mod:`app.modules.rules.models`, which is the *schema* of the rule store —
what a rule looks like on disk. These are what an evaluation of one hands back. A reader
chasing "how is a rule written" and a reader chasing "what did evaluating it produce" are
answering different questions, and the two files had grown past one file's worth anyway.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Literal

from pydantic import Field

from .base import (
    NonEmptyText,
    NonNegativeDecimal,
    OverrideTarget,
    PositiveDecimal,
    ProductCategory,
    Rule7Route,
    ScopeStatus,
    StrictRuleModel,
    Verdict,
    WidthRatioResult,
)


class SectorOverride(StrictRuleModel):
    """One confirmed-category routing decision, traced to the rule that made it.

    ``rule_id`` travels with the framework name so a finding can be re-derived: an
    officer asked why a medical device was not measured against Table-I gets the gazette,
    not an assertion.
    """

    sector: ProductCategory
    target: OverrideTarget
    controlling_framework: str
    rule_id: str


class ScopeDecision(StrictRuleModel):
    """Whether Chapter II reaches one package, and the limb of Rule 3 that says so.

    ``limb`` and ``rule_id`` travel with the status for the same reason they do on
    :class:`SectorOverride`: an officer asked why a 30 kilogram sack bore no findings gets
    the clause, not an assertion. ``limb`` is ``None`` exactly when ``status`` is
    :attr:`~app.modules.rules.base.ScopeStatus.GOVERNED` — no limb fired, so there is none
    to name.

    ``reason`` is written for the officer reading the finding, not for a log.
    """

    status: ScopeStatus
    reason: NonEmptyText
    rule_id: NonEmptyText
    limb: NonEmptyText | None = None


class Rule7HeightEvaluation(StrictRuleModel):
    """Return the controlling route and safe verdict for character height.

    ``override`` is populated exactly when ``route`` is
    :attr:`~app.modules.rules.base.Rule7Route.SECTOR_FRAMEWORK`, and names the framework
    and the rule that routed there. ``required_height_mm`` is ``None`` in that case: this
    module encodes no thresholds from another framework and will not infer one.
    """

    route: Rule7Route
    verdict: Verdict
    required_height_mm: Decimal | None
    override: SectorOverride | None = None


class Rule7WidthEvaluation(StrictRuleModel):
    """Return the controlling route and safe verdict for character width."""

    route: Rule7Route
    verdict: Verdict
    ratio_result: WidthRatioResult | None
    override: SectorOverride | None = None


class SideClearance(StrictRuleModel):
    """Free space between the declaration and whatever bounds it on one side.

    ``distance_mm`` is ``ge=0`` because a declaration flush against its neighbour has a
    clearance of exactly zero. That is a physical fact about the package and not a failed
    measurement, and typing it ``gt=0`` is what made a flush declaration — the reading that
    breaches the proviso outright — impossible to hand to the evaluator at all.

    Zero is a clearance and never an overlap. One physical fact, one representation: the
    same boundary :class:`~app.contracts.MeasurementMarginExact` draws with ``ge=0`` against
    :class:`~app.contracts.MeasurementMarginOverlapExact`'s ``gt=0``, so the two vocabularies
    line up member for member and translating between them needs no arithmetic.
    """

    state: Literal["clearance"] = "clearance"
    distance_mm: NonNegativeDecimal


class SideOverlap(StrictRuleModel):
    """Neighbouring ink intruding into the free space on one side.

    A measurement that succeeded and came back negative, not a measurement that failed.
    Carried as a positive magnitude under its own name, so nothing reading a clearance off
    a side can pick up an intrusion by mistake — the direction is carried by the type and
    never by a sign. The sibling of :attr:`SideClearance.distance_mm` in
    ``app.contracts`` makes the same choice for the same reason.

    ``gt=0``: zero is a flush declaration, which is a :class:`SideClearance`.
    """

    state: Literal["overlap"] = "overlap"
    overlap_mm: PositiveDecimal


SideSpace = Annotated[SideClearance | SideOverlap, Field(discriminator="state")]
"""What was found on one side of the declaration: clearance, or ink crossing into it.

Two variants and not three. A flush declaration is a clearance of zero rather than a state
of its own, because giving it a third variant would give one physical fact two
representations — ``SideClearance(distance_mm=0)`` and a bare ``SideFlush`` — which is the
ambiguity ``app.contracts`` refuses when it declines to admit ``0.0`` as an overlap.
"""


class FreeSpaceMeasurement(StrictRuleModel):
    """Calibrated readings around a quantity declaration, one per side.

    Rule 8(1)'s proviso is breached by two readings and satisfied by one, so a side is a
    :data:`SideSpace` rather than a number: an evaluator has to say which of the three it
    received before it can compare anything, and no sign check is available to skip. A
    clearance of 2 mm and an intrusion of 2 mm are different facts about a package, and
    when both were a positive ``Decimal`` in one field nothing was obliged to tell them
    apart.

    Rule 8(1) is geometrically measurable and this is the measurement it is measurable
    *from* — the caller supplies figures already calibrated against a reference object or
    taken from pre-print artwork. A millimetre figure is never derived from an uncalibrated
    photograph, and this model cannot tell the difference, so the obligation stays with the
    caller that owns the calibration.

    The proviso scales with the *numeral's* height, which is why that is the one height
    this model carries. A letter height is Rule 7's question and is not an input here.
    """

    numeral_height_mm: PositiveDecimal
    space_above: SideSpace
    space_below: SideSpace
    space_left: SideSpace
    space_right: SideSpace


class Rule8FreeSpaceEvaluation(StrictRuleModel):
    """Return the Rule 8(1) proviso outcome and the sides that fell short.

    ``deficient_sides`` names the sides rather than counting them: "left" and "right"
    carry the doubled requirement, so which side failed is what an officer needs to look
    at, and an empty tuple is the only shape a ``PASS`` can take.

    ``overlapping_sides`` is the subset of those where ink actually crosses into the free
    space. It is reported separately because the two are different facts an officer acts on
    differently — space that exists but falls short, against no space at all and a neighbour
    encroaching — and folding them into one list would rebuild at the reporting layer the
    ambiguity :data:`SideSpace` removes at the data layer. Every overlapping side is also a
    deficient side; the reverse does not hold.
    """

    verdict: Verdict
    required_above_below_mm: Decimal
    required_left_right_mm: Decimal
    deficient_sides: tuple[str, ...]
    overlapping_sides: tuple[str, ...]
