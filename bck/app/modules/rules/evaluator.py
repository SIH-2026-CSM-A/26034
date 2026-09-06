"""Deterministic helpers for evaluating the legal rules encoded by RUL-001."""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from app.contracts import DeclarationField

from .base import (
    OverrideTarget,
    ProductCategory,
    Rule7Route,
    RuleStatus,
    Verdict,
    WidthRatioResult,
)
from .conditions import (
    NumericConstraint,
    OtherLawCarveOutCondition,
    PdpAreaCondition,
    TableHeightCondition,
    WidthRatioCondition,
)
from .loader import rule_by_id
from .models import RuleDefinition
from .results import Rule7HeightEvaluation, Rule7WidthEvaluation
from .sector import SectorRoutedError, controlling_framework

TABLE_I_RULE_ID = "R7-2-TABLE-I"
WIDTH_RATIO_RULE_ID = "R7-3-WIDTH-RATIO"
PDP_AREA_RULE_ID = "R7-4-PDP-AREA"
OTHER_LAW_CARVE_OUT_RULE_ID = "R7-5-OTHER-LAW"


def _positive(value: Decimal, field_name: str) -> Decimal:
    """Reject non-finite or non-positive numeric evidence."""
    if not value.is_finite() or value <= 0:
        raise ValueError(f"{field_name} must be finite and greater than zero")
    return value


def evaluate_rule(rule: RuleDefinition, proposed_verdict: Verdict) -> Verdict:
    """Apply the central source-status gate to every proposed rule verdict."""
    if rule.status is RuleStatus.UNVERIFIED:
        return Verdict.REVIEW
    return proposed_verdict


def evaluate_numeric_constraint(
    condition: NumericConstraint,
    *,
    declared_value: Decimal,
    expected_value: Decimal,
) -> bool:
    """Evaluate either rounding or tolerance without conflating their semantics."""
    if condition.rounding_increment is not None:
        increment = condition.rounding_increment
        rounded_units = (expected_value / increment).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return declared_value == rounded_units * increment

    if condition.tolerance is None:
        raise ValueError("numeric constraint has no comparison concept")
    return abs(declared_value - expected_value) <= condition.tolerance


def minimum_character_height(
    panel_area: Decimal,
    *,
    is_blown_formed_or_moulded: bool,
    product_category: ProductCategory | None,
    evaluation_date: date,
) -> Decimal:
    """Return the Rule 7 Table-I height for a supplied positive PDP area.

    **Table-I is not universal.** G.S.R. 778(E) routes the height of any numeral and
    letter on a medical device package to the Medical Devices Rules, 2017, so a Table-I
    figure is not merely the wrong number for such a package — it is a requirement from a
    provision that does not apply to it. The guard sits in this lookup rather than in the
    two evaluators that call it because this function is exported: a sector-blind caller
    reaching it directly is exactly how a Table-I band reaches a medical device, and one
    guard here covers every caller instead of one guard per callsite.

    Raises :class:`~app.modules.rules.sector.SectorRoutedError` when a sector override
    controls character height, and :class:`ValueError` for a non-positive area.
    """
    routed = controlling_framework(
        OverrideTarget.TABLE_HEIGHT,
        product_category,
        evaluation_date,
    )
    if routed is not None:
        raise SectorRoutedError(
            f"character height for {routed.sector} packages is governed by "
            f"{routed.controlling_framework} per rule {routed.rule_id}; Rule 7 Table-I "
            f"does not apply"
        )

    area = _positive(panel_area, "panel_area")
    condition = rule_by_id(TABLE_I_RULE_ID).conditions
    if not isinstance(condition, TableHeightCondition):
        raise TypeError(f"{TABLE_I_RULE_ID} does not contain a table-height condition")

    for band in condition.bands:
        above_minimum = (
            band.minimum_area_exclusive_cm2 is None or area > band.minimum_area_exclusive_cm2
        )
        within_maximum = (
            band.maximum_area_inclusive_cm2 is None or area <= band.maximum_area_inclusive_cm2
        )
        if above_minimum and within_maximum:
            if is_blown_formed_or_moulded:
                return band.moulded_minimum_height_mm
            return band.normal_minimum_height_mm

    raise ValueError(f"no Rule 7 Table-I band covers panel area {area}")


def validate_width_to_height(
    character: str,
    width: Decimal,
    height: Decimal,
) -> WidthRatioResult:
    """Evaluate Rule 7(3) while preserving each named character exception."""
    condition = rule_by_id(WIDTH_RATIO_RULE_ID).conditions
    if not isinstance(condition, WidthRatioCondition):
        raise TypeError(f"{WIDTH_RATIO_RULE_ID} does not contain a width-ratio condition")
    if character in condition.exempt_characters:
        return WidthRatioResult.EXEMPT

    character_width = _positive(width, "width")
    character_height = _positive(height, "height")
    if character_width / character_height >= condition.minimum_width_to_height_ratio:
        return WidthRatioResult.MEETS
    return WidthRatioResult.DOES_NOT_MEET


def calculate_rectangular_pdp_area(height: Decimal, width: Decimal) -> Decimal:
    """Calculate rectangular PDP area from the supplied display side."""
    return _positive(height, "height") * _positive(width, "width")


def calculate_cylindrical_pdp_area(
    height: Decimal,
    circumference: Decimal,
    *,
    nearly_cylindrical: bool = False,
) -> Decimal:
    """Calculate cylindrical or nearly cylindrical PDP area using Rule 7(4)."""
    del nearly_cylindrical
    condition = rule_by_id(PDP_AREA_RULE_ID).conditions
    if not isinstance(condition, PdpAreaCondition):
        raise TypeError(f"{PDP_AREA_RULE_ID} does not contain a PDP-area condition")
    return (
        condition.cylindrical_multiplier
        * _positive(height, "height")
        * _positive(circumference, "circumference")
    )


def calculate_other_shape_pdp_area(
    *,
    total_surface_area: Decimal | None = None,
    excluded_surface_area: Decimal = Decimal("0"),
    legally_applicable_pdp_area: Decimal | None = None,
) -> Decimal:
    """Calculate another shape by exactly one Rule 7(4) alternative."""
    condition = rule_by_id(PDP_AREA_RULE_ID).conditions
    if not isinstance(condition, PdpAreaCondition):
        raise TypeError(f"{PDP_AREA_RULE_ID} does not contain a PDP-area condition")
    if (total_surface_area is None) == (legally_applicable_pdp_area is None):
        raise ValueError("provide exactly one other-shape PDP-area basis")
    if legally_applicable_pdp_area is not None:
        if not condition.allow_legally_identified_pdp_area:
            raise ValueError("the rule store does not allow an identified PDP area")
        return _positive(legally_applicable_pdp_area, "legally_applicable_pdp_area")

    assert total_surface_area is not None
    total = _positive(total_surface_area, "total_surface_area")
    if not excluded_surface_area.is_finite() or excluded_surface_area < 0:
        raise ValueError("excluded_surface_area must be finite and non-negative")
    eligible_surface = total - excluded_surface_area
    return condition.other_shape_multiplier * _positive(eligible_surface, "eligible_surface")


def rule7_requirements_apply(
    declaration: str,
    *,
    required_under_other_law: bool,
) -> bool:
    """Apply the Rule 7(5) carve-out while retaining preserved sizing groups."""
    if not required_under_other_law:
        return True
    condition = rule_by_id(OTHER_LAW_CARVE_OUT_RULE_ID).conditions
    if not isinstance(condition, OtherLawCarveOutCondition):
        raise TypeError(f"{OTHER_LAW_CARVE_OUT_RULE_ID} has the wrong condition type")
    return declaration in condition.preserved_declarations


def evaluate_rule7_height(
    *,
    panel_area: Decimal,
    measured_height: Decimal,
    is_blown_formed_or_moulded: bool,
    product_category: ProductCategory | None,
    evaluation_date: date,
) -> Rule7HeightEvaluation:
    """Route a carved-out sector to its own framework, others through Table-I.

    A routed package returns ``REVIEW`` with no ``required_height_mm``: this module has
    no Medical Devices Rules, 2017 thresholds encoded and will not invent one, so the
    honest output is that the packaged rules do not decide it.
    """
    routed = controlling_framework(
        OverrideTarget.TABLE_HEIGHT,
        product_category,
        evaluation_date,
    )
    if routed is not None:
        return Rule7HeightEvaluation(
            route=Rule7Route.SECTOR_FRAMEWORK,
            verdict=Verdict.REVIEW,
            required_height_mm=None,
            override=routed,
        )

    required_height = minimum_character_height(
        panel_area,
        is_blown_formed_or_moulded=is_blown_formed_or_moulded,
        product_category=product_category,
        evaluation_date=evaluation_date,
    )
    observed_height = _positive(measured_height, "measured_height")
    proposed = Verdict.PASS if observed_height >= required_height else Verdict.POTENTIAL_VIOLATION
    verdict = evaluate_rule(rule_by_id(TABLE_I_RULE_ID), proposed)
    return Rule7HeightEvaluation(
        route=Rule7Route.LMPC_TABLE_I,
        verdict=verdict,
        required_height_mm=required_height,
    )


def evaluate_rule7_width(
    *,
    character: str,
    width: Decimal,
    height: Decimal,
    product_category: ProductCategory | None,
    evaluation_date: date,
) -> Rule7WidthEvaluation:
    """Route a carved-out sector to its own framework, others through Rule 7(3)."""
    routed = controlling_framework(
        OverrideTarget.WIDTH_RATIO,
        product_category,
        evaluation_date,
    )
    if routed is not None:
        return Rule7WidthEvaluation(
            route=Rule7Route.SECTOR_FRAMEWORK,
            verdict=Verdict.REVIEW,
            ratio_result=None,
            override=routed,
        )

    ratio_result = validate_width_to_height(character, width, height)
    proposed = (
        Verdict.POTENTIAL_VIOLATION
        if ratio_result is WidthRatioResult.DOES_NOT_MEET
        else Verdict.PASS
    )
    verdict = evaluate_rule(rule_by_id(WIDTH_RATIO_RULE_ID), proposed)
    return Rule7WidthEvaluation(
        route=Rule7Route.LMPC_TABLE_I,
        verdict=verdict,
        ratio_result=ratio_result,
    )


def select_effective_rule(
    rules: tuple[RuleDefinition, ...],
    clause_ref: str,
    evaluation_date: date,
) -> RuleDefinition | None:
    """Select the latest rule version active for a clause on a supplied date."""
    active = [
        rule
        for rule in rules
        if rule.clause_ref == clause_ref
        and rule.effective_from <= evaluation_date
        and (rule.effective_to is None or evaluation_date <= rule.effective_to)
    ]
    if not active:
        return None
    return max(active, key=lambda rule: (rule.effective_from, rule.rule_id))


def rule_governs_declaration(rule: RuleDefinition, field: DeclarationField) -> bool:
    """Return whether a rule governs the given declaration field.

    When ``rule.governs_declarations`` is ``None``, the rule falls back to broad
    evaluation across all declarations (returns ``True``). Otherwise returns ``True``
    only if ``field`` is in ``rule.governs_declarations``.
    """
    return rule.governs(field)


def declarations_governed_by_rule(
    rule: RuleDefinition,
    candidate_fields: tuple[DeclarationField, ...],
) -> tuple[DeclarationField, ...]:
    """Return candidate declaration fields governed by the supplied rule.

    If ``rule.governs_declarations`` is ``None``, candidate fields are returned
    unfiltered (broad evaluation fallback). Otherwise, only fields present in
    ``rule.governs_declarations`` are returned.
    """
    if rule.governs_declarations is None:
        return candidate_fields
    return tuple(field for field in candidate_fields if field in rule.governs_declarations)
