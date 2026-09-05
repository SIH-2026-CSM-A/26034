"""Public API for the deterministic legal rule store."""

from .evaluator import (
    calculate_cylindrical_pdp_area,
    calculate_other_shape_pdp_area,
    calculate_rectangular_pdp_area,
    evaluate_numeric_constraint,
    evaluate_rule,
    evaluate_rule7_height,
    evaluate_rule7_width,
    minimum_character_height,
    rule7_requirements_apply,
    select_effective_rule,
    validate_width_to_height,
)
from .loader import RuleLoadError, load_rules
from .models import (
    NumericConstraint,
    Rule7Route,
    RuleDefinition,
    RuleStatus,
    Verdict,
    WidthRatioResult,
)

__all__ = [
    "NumericConstraint",
    "Rule7Route",
    "RuleDefinition",
    "RuleLoadError",
    "RuleStatus",
    "Verdict",
    "WidthRatioResult",
    "calculate_cylindrical_pdp_area",
    "calculate_other_shape_pdp_area",
    "calculate_rectangular_pdp_area",
    "evaluate_numeric_constraint",
    "evaluate_rule",
    "evaluate_rule7_height",
    "evaluate_rule7_width",
    "load_rules",
    "minimum_character_height",
    "rule7_requirements_apply",
    "select_effective_rule",
    "validate_width_to_height",
]
