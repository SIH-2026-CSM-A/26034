"""Strict models for the deterministic legal rule store."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
PositiveDecimal = Annotated[Decimal, Field(gt=0)]
NonNegativeDecimal = Annotated[Decimal, Field(ge=0)]


class StrictRuleModel(BaseModel):
    """Reject fields outside each declared rule-store schema."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class RuleStatus(StrEnum):
    """Represent the permitted legal-source verification states."""

    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"


class Verdict(StrEnum):
    """Represent decision-support outcomes without making legal determinations."""

    PASS = "PASS"
    REVIEW = "REVIEW"
    POTENTIAL_VIOLATION = "POTENTIAL VIOLATION"


class Severity(StrEnum):
    """Represent the outcome used when a verified rule condition is not met."""

    REVIEW = "REVIEW"
    POTENTIAL_VIOLATION = "POTENTIAL VIOLATION"


class Rule7Route(StrEnum):
    """Identify which legal framework controls character sizing."""

    LMPC_TABLE_I = "LMPC_TABLE_I"
    MEDICAL_DEVICES_RULES_2017 = "MEDICAL_DEVICES_RULES_2017"


class WidthRatioResult(StrEnum):
    """Represent Rule 7(3) ratio applicability and deterministic comparison."""

    MEETS = "MEETS"
    DOES_NOT_MEET = "DOES_NOT_MEET"
    EXEMPT = "EXEMPT"


class DeclarationRequiredCondition(StrictRuleModel):
    """Describe mandatory declarations and their source-defined exceptions."""

    kind: Literal["declaration_required"]
    declarations: tuple[NonEmptyText, ...] = Field(min_length=1)
    exceptions: tuple[NonEmptyText, ...]


class TableBand(StrictRuleModel):
    """Describe one inclusive-upper-bound Rule 7 Table-I band."""

    minimum_area_exclusive_cm2: NonNegativeDecimal | None
    maximum_area_inclusive_cm2: PositiveDecimal | None
    normal_minimum_height_mm: PositiveDecimal
    moulded_minimum_height_mm: PositiveDecimal


class TableHeightCondition(StrictRuleModel):
    """Describe the complete Rule 7 Table-I height lookup."""

    kind: Literal["table_height"]
    bands: tuple[TableBand, ...] = Field(min_length=1)


class WidthRatioCondition(StrictRuleModel):
    """Describe the Rule 7(3) width-to-height threshold and exceptions."""

    kind: Literal["width_ratio"]
    minimum_width_to_height_ratio: PositiveDecimal
    exempt_characters: tuple[NonEmptyText, ...] = Field(min_length=1)


class PdpAreaCondition(StrictRuleModel):
    """Describe Rule 7(4) PDP formulas and excluded package regions."""

    kind: Literal["pdp_area"]
    cylindrical_multiplier: PositiveDecimal
    other_shape_multiplier: PositiveDecimal
    allow_legally_identified_pdp_area: bool
    excluded_regions: tuple[NonEmptyText, ...] = Field(min_length=1)


class OtherLawCarveOutCondition(StrictRuleModel):
    """Describe Rule 7(5) declarations whose sizing remains preserved."""

    kind: Literal["other_law_carve_out"]
    preserved_declarations: tuple[NonEmptyText, ...] = Field(min_length=1)


class SectorOverrideCondition(StrictRuleModel):
    """Describe deterministic routing to a controlling sector framework."""

    kind: Literal["sector_override"]
    sector: Literal["medical_device"]
    controlling_framework: Literal["Medical Devices Rules, 2017"]
    overrides: tuple[Literal["table_height", "width_ratio"], ...] = Field(min_length=1)


class EcommerceFilterCondition(StrictRuleModel):
    """Describe the country-of-origin filter required for imported listings."""

    kind: Literal["ecommerce_country_of_origin_filter"]
    imported_products_only: Literal[True]
    searchable: Literal[True]
    sortable: Literal[True]


class NumericConstraint(StrictRuleModel):
    """Keep rounding-increment and tolerance semantics explicitly separate."""

    kind: Literal["numeric_constraint"]
    rounding_increment: PositiveDecimal | None = None
    tolerance: NonNegativeDecimal | None = None

    @model_validator(mode="after")
    def require_exactly_one_numeric_concept(self) -> NumericConstraint:
        """Require one comparison concept so rounding cannot alias tolerance."""
        values = (self.rounding_increment, self.tolerance)
        if sum(value is not None for value in values) != 1:
            raise ValueError("exactly one of rounding_increment or tolerance is required")
        return self


RuleCondition = Annotated[
    DeclarationRequiredCondition
    | TableHeightCondition
    | WidthRatioCondition
    | PdpAreaCondition
    | OtherLawCarveOutCondition
    | SectorOverrideCondition
    | EcommerceFilterCondition
    | NumericConstraint,
    Field(discriminator="kind"),
]


class RuleDefinition(StrictRuleModel):
    """RUL-001 stand-in; CTR-002 migration is an app.contracts import substitution."""

    rule_id: NonEmptyText
    clause_ref: NonEmptyText
    gazette_ref: NonEmptyText
    source_text: NonEmptyText
    status: RuleStatus
    effective_from: date
    effective_to: date | None
    applies_to: tuple[NonEmptyText, ...] = Field(min_length=1)
    conditions: RuleCondition
    evidence_requirement: NonEmptyText
    severity: Severity

    @field_validator("gazette_ref")
    @classmethod
    def validate_gazette_filename(cls, value: str) -> str:
        """Require a bare PDF filename rather than a path or empty reference."""
        if Path(value).name != value or not value.lower().endswith(".pdf"):
            raise ValueError("gazette_ref must be a bare PDF filename")
        return value

    @model_validator(mode="after")
    def validate_effective_window(self) -> RuleDefinition:
        """Reject an effective interval whose end precedes its start."""
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError("effective_to cannot precede effective_from")
        return self


class RuleStoreDocument(StrictRuleModel):
    """Describe the versioned top-level YAML rule-store document."""

    schema_version: Literal[1]
    rules: tuple[RuleDefinition, ...] = Field(min_length=1)


class Rule7HeightEvaluation(StrictRuleModel):
    """Return the controlling route and safe verdict for character height."""

    route: Rule7Route
    verdict: Verdict
    required_height_mm: Decimal | None


class Rule7WidthEvaluation(StrictRuleModel):
    """Return the controlling route and safe verdict for character width."""

    route: Rule7Route
    verdict: Verdict
    ratio_result: WidthRatioResult | None
