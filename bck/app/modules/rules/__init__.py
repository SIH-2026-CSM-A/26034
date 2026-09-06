"""Public API for the deterministic legal rule store.

Everything another package needs is named here. ``app.pipeline`` composes this module and
must be able to do so without knowing which file inside it holds what — a deep import into
``.models`` or ``.conditions`` couples a caller to this module's internal layout, and
import-linter cannot see the difference between that and a legitimate package import.
"""

from .base import (
    ConstituentSimilarity,
    OverrideTarget,
    PackageType,
    ProductCategory,
    Rule7Route,
    RuleStatus,
    Severity,
    Verdict,
    WidthRatioResult,
)
from .conditions import (
    DeclarationMannerCondition,
    DeclarationRequiredCondition,
    FreeSpaceCondition,
    NumericConstraint,
    OuterContainerCondition,
    PackageDefinitionCondition,
    PlacementCondition,
    RuleCondition,
    SectorOverrideCondition,
)
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
from .loader import RuleLoadError, is_active, load_rules, rule_by_id
from .models import RuleDefinition, RuleStoreDocument
from .placement import evaluate_rule8_free_space, required_declaration_location
from .results import (
    FreeSpaceMeasurement,
    Rule7HeightEvaluation,
    Rule7WidthEvaluation,
    Rule8FreeSpaceEvaluation,
    SectorOverride,
)
from .sector import (
    SectorRoutedError,
    controlling_framework,
    pdp_declaration_mandatory,
    rule_33_relaxation_applies,
    sector_overrides,
)

__all__ = [
    "ConstituentSimilarity",
    "DeclarationMannerCondition",
    "DeclarationRequiredCondition",
    "FreeSpaceCondition",
    "FreeSpaceMeasurement",
    "NumericConstraint",
    "OuterContainerCondition",
    "OverrideTarget",
    "PackageDefinitionCondition",
    "PackageType",
    "PlacementCondition",
    "ProductCategory",
    "Rule7HeightEvaluation",
    "Rule7Route",
    "Rule7WidthEvaluation",
    "Rule8FreeSpaceEvaluation",
    "RuleCondition",
    "RuleDefinition",
    "RuleLoadError",
    "RuleStatus",
    "RuleStoreDocument",
    "SectorOverride",
    "SectorOverrideCondition",
    "SectorRoutedError",
    "Severity",
    "Verdict",
    "WidthRatioResult",
    "calculate_cylindrical_pdp_area",
    "calculate_other_shape_pdp_area",
    "calculate_rectangular_pdp_area",
    "controlling_framework",
    "evaluate_numeric_constraint",
    "evaluate_rule",
    "evaluate_rule7_height",
    "evaluate_rule7_width",
    "evaluate_rule8_free_space",
    "is_active",
    "load_rules",
    "minimum_character_height",
    "pdp_declaration_mandatory",
    "required_declaration_location",
    "rule7_requirements_apply",
    "rule_33_relaxation_applies",
    "rule_by_id",
    "sector_overrides",
    "select_effective_rule",
    "validate_width_to_height",
]
