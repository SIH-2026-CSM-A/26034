"""Rules that state a physical threshold, and the one place a millimetre may be emitted.

Every path in this module that lacks a usable measurement returns INSUFFICIENT_EVIDENCE
carrying the refusal's own reason and **no figure of any kind**. That is the module's
whole purpose. A millimetre value derived from an uncalibrated photograph is pixels with a
unit attached: an officer cannot act on it, and nothing downstream could tell it apart
from a figure the gazette actually states.

The type system does most of the work. :class:`~app.contracts.MeasurementRefusal` has no
``value`` and no ``unit`` field to read even by accident, and ``extra="forbid"`` stops one
being smuggled in, so a refusal cannot become a number by mistake. What this module adds
is the second half: a refusal never reaches an evaluator, so no *required* threshold is
looked up on its behalf either. Rule 7 Table-I would happily return a band for any area
you gave it.

**Requirements may carry millimetres; observations may not.** A finding's
``expected_value`` states what the rule requires and is a quotation from the gazette, so
it carries a figure whenever the rule states one. ``observed_value`` and ``reason``
describe what we saw, and carry a figure only where a real measurement was made.
"""

from decimal import Decimal

from app.contracts import (
    DeclarationField,
    FieldFinding,
    FieldState,
    MeasurementCalibrated,
    MeasurementRefusal,
)
from app.modules.rules import RuleDefinition, evaluate_rule7_height
from app.pipeline.dispositions import FIELD_STATE_FROM_VERDICT
from app.pipeline.rule_findings import EvidenceContext, finding

NO_ATTEMPT = "no measurement was attempted for this rule."


def measurement_findings(
    rule: RuleDefinition, fields: tuple[DeclarationField, ...], context: EvidenceContext
) -> list[FieldFinding]:
    """Findings for a rule that states a physical threshold."""
    result = context.measurements.get(rule.conditions.kind)
    if result is None or isinstance(result, MeasurementRefusal):
        reason = result.reason if isinstance(result, MeasurementRefusal) else NO_ATTEMPT
        return _refused(
            rule, fields, context, f"the measurement this rule needs was not made: {reason}"
        )

    if rule.conditions.kind == "table_height":
        return _table_height(rule, fields, context, result)

    # A ratio and a clearance were each measured, and neither rule can be resolved from
    # the figure alone: Rule 7(3) exempts named characters and this pipeline does not yet
    # identify which character a ratio belongs to, while Rule 8(1)'s proviso compares four
    # clearances against the numeral's own height rather than one scalar. Saying so is the
    # honest output; guessing the character would decide a finding on the guess.
    return [
        finding(
            rule,
            field,
            FieldState.REVIEW_REQUIRED,
            "a measurement was taken, but resolving this rule from it needs a person: "
            f"{rule.evidence_requirement}.",
            context,
            observed_value=f"{result.value:.2f} {result.unit}",
        )
        for field in fields
    ]


def _refused(
    rule: RuleDefinition,
    fields: tuple[DeclarationField, ...],
    context: EvidenceContext,
    reason: str,
) -> list[FieldFinding]:
    """INSUFFICIENT_EVIDENCE across every declaration the rule governs, and no figure.

    Not FAIL, and never in the same branch as one. The package may well comply; we did not
    obtain the evidence to say either way, which is a defect in our reading rather than in
    the package, and only the latter can support enforcement.
    """
    return [
        finding(rule, field, FieldState.INSUFFICIENT_EVIDENCE, reason, context) for field in fields
    ]


def _table_height(
    rule: RuleDefinition,
    fields: tuple[DeclarationField, ...],
    context: EvidenceContext,
    height: object,
) -> list[FieldFinding]:
    """Rule 7(2) Table-I: band the measured character height against the panel area.

    Both figures must be real. Table-I bands a height against an *area*, so a height with
    no panel area behind it cannot be compared to anything, and looking up a band for a
    guessed area would produce a millimetre requirement with no basis.
    """
    panel = context.measurements.get("pdp_area")
    if panel is None or isinstance(panel, MeasurementRefusal):
        # The height is real and is the officer's to use; it is the band that is missing.
        why = panel.reason if isinstance(panel, MeasurementRefusal) else NO_ATTEMPT
        return [
            finding(
                rule,
                field,
                FieldState.INSUFFICIENT_EVIDENCE,
                "the character height was measured but the principal display panel area was "
                f"not, and Table-I bands the height against that area: {why}",
                context,
                observed_value=f"{height.value:.2f} {height.unit}",
            )
            for field in fields
        ]

    def evaluate(area_cm2: float, height_mm: float = height.value):
        # An interval reaching below zero reaches the first band, whose lower edge is open.
        return evaluate_rule7_height(
            panel_area=Decimal(str(max(area_cm2, 1e-6))),
            measured_height=Decimal(str(max(height_mm, 1e-6))),
            is_blown_formed_or_moulded=False,
            product_category=context.product_category,
            evaluation_date=context.evaluation_date,
        )

    evaluation = evaluate(panel.value)
    # The band is a legal threshold and both figures carry an interval. Where the verdict
    # differs between the ends of either interval, which side of the requirement the
    # package falls on is exactly what the measurement cannot say at its own precision:
    # the officer's call, REVIEW_REQUIRED, never FAIL. Agreeing verdicts at every end
    # stand as measured.
    areas, heights = _ends(panel), _ends(height)
    if {evaluate(a, h).verdict for a in areas for h in heights} != {evaluation.verdict}:
        bands = sorted({evaluate(a).required_height_mm for a in areas} - {None})
        straddled = [b for b in bands if heights[0] < b <= heights[-1]]
        uncertain = []
        if len(bands) > 1:
            uncertain.append(
                "the measured principal display panel area of "
                f"{panel.value:.1f} ± {panel.confidence_interval:.1f} {panel.unit} lies across "
                f"a Table-I band edge: {bands[0]} mm is required below it and {bands[-1]} mm "
                "above"
            )
        if straddled:
            uncertain.append(
                f"the measured character height of {_with_interval(height)} lies across the "
                f"{' and '.join(f'{b} mm' for b in straddled)} requirement"
            )
        else:
            uncertain.append(
                f"the measured character height of {_with_interval(height)} meets one band "
                "and not the other"
            )
        return [
            finding(
                rule,
                field,
                FieldState.REVIEW_REQUIRED,
                "; ".join(uncertain) + ": which side of the requirement this package falls "
                "on is not established at the measurement's own precision.",
                context,
                observed_value=f"{height.value:.2f} {height.unit}",
                expected_value=" to ".join(f"{b} mm" for b in bands),
            )
            for field in fields
        ]
    required = evaluation.required_height_mm
    return [
        finding(
            rule,
            field,
            FIELD_STATE_FROM_VERDICT[evaluation.verdict],
            "the measured character height was compared against the Table-I band for the "
            f"measured principal display panel area of {panel.value:.1f} {panel.unit}.",
            context,
            observed_value=f"{height.value:.2f} {height.unit}",
            expected_value=None if required is None else f"{required} mm",
        )
        for field in fields
    ]


def _ends(result: object) -> tuple[float, ...]:
    """Both ends of a calibrated figure's interval; the point value of any other."""
    if isinstance(result, MeasurementCalibrated):
        return (
            result.value - result.confidence_interval,
            result.value + result.confidence_interval,
        )
    return (result.value,)


def _with_interval(result: object) -> str:
    """``2.61 ± 0.13 mm`` for a calibrated figure, ``2.61 mm`` for any other."""
    if isinstance(result, MeasurementCalibrated):
        return f"{result.value:.2f} ± {result.confidence_interval:.2f} {result.unit}"
    return f"{result.value:.2f} {result.unit}"
