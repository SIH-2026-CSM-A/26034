"""Return shapes for the deterministic rule evaluations in this module.

Kept apart from :mod:`app.modules.rules.models`, which is the *schema* of the rule store —
what a rule looks like on disk. These are what an evaluation of one hands back. A reader
chasing "how is a rule written" and a reader chasing "what did evaluating it produce" are
answering different questions, and the two files had grown past one file's worth anyway.
"""

from __future__ import annotations

from decimal import Decimal

from .base import (
    OverrideTarget,
    PositiveDecimal,
    ProductCategory,
    Rule7Route,
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


class FreeSpaceMeasurement(StrictRuleModel):
    """Calibrated clearances around a quantity declaration, in millimetres.

    Every field is a positive ``Decimal``, so an absent or zero clearance fails to
    construct rather than evaluating as a pass. Rule 8(1) is geometrically measurable and
    this is the measurement it is measurable *from* — the caller supplies figures already
    calibrated against a reference object or taken from pre-print artwork. A millimetre
    figure is never derived from an uncalibrated photograph, and this model cannot tell
    the difference, so the obligation stays with the caller that owns the calibration.
    """

    numeral_height_mm: PositiveDecimal
    space_above_mm: PositiveDecimal
    space_below_mm: PositiveDecimal
    space_left_mm: PositiveDecimal
    space_right_mm: PositiveDecimal


class Rule8FreeSpaceEvaluation(StrictRuleModel):
    """Return the Rule 8(1) proviso outcome and the clearances that fell short.

    ``deficient_sides`` names the sides rather than counting them: "left" and "right"
    carry the doubled requirement, so which side failed is what an officer needs to look
    at, and an empty tuple is the only shape a ``PASS`` can take.
    """

    verdict: Verdict
    required_above_below_mm: Decimal
    required_left_right_mm: Decimal
    deficient_sides: tuple[str, ...]
