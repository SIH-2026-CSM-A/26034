"""Shared vocabulary for the rule store: value constraints and closed enumerations.

Imports nothing from this package, so the schema files below it can depend on it in one
direction and no other. Splitting it out is what the 300-line limit bought — the rule
store grew a placement rule, a manner rule, two package definitions and a sector dispatch
in RUL-002, and one file could no longer hold the schema and stay readable.
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

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


class ProductCategory(StrEnum):
    """Represent a *confirmed* product category that a sector override may key on.

    Confirmed is the operative word. A category is an input to routing, never an
    inference this module makes: routing a package to another Act because a classifier
    guessed at its category would move a real legal obligation on a guess. A caller with
    no confirmed category passes ``None`` and the packaged rules apply unchanged.
    """

    FOOD = "food"
    COSMETICS = "cosmetics"
    MEDICAL_DEVICE = "medical_device"


class OverrideTarget(StrEnum):
    """Identify which obligation a sector override moves to another framework.

    ``PDP_DECLARATION`` is Rule 2(h), ``MANUFACTURER_DECLARATION`` is Rule 6(1)(a) and
    ``DATE_DECLARATION`` is Rule 6(1)(d); the other two are Rule 7(2) and Rule 7(3).
    """

    TABLE_HEIGHT = "table_height"
    WIDTH_RATIO = "width_ratio"
    PDP_DECLARATION = "pdp_declaration"
    MANUFACTURER_DECLARATION = "manufacturer_declaration"
    DATE_DECLARATION = "date_declaration"


class PackageType(StrEnum):
    """Identify a package composition the rules define rather than measure."""

    COMBINATION_PACKAGE = "combination_package"
    GROUP_PACKAGE = "group_package"


class ConstituentSimilarity(StrEnum):
    """Distinguish the two package definitions inserted by G.S.R. 722(E)."""

    DISSIMILAR = "dissimilar"
    SIMILAR_BUT_NOT_IDENTICAL = "similar_but_not_identical"


class Rule7Route(StrEnum):
    """Identify whether the packaged rules or a sector framework controls sizing.

    Deliberately *not* one member per framework. Naming the Medical Devices Rules, 2017
    here would put the one sector that exists today inside the dispatch, so adding the
    next sector would mean editing this enum and every comparison against it. Which
    framework took over is carried by value on
    :class:`~app.modules.rules.results.SectorOverride`, alongside the rule that says so.
    """

    LMPC_TABLE_I = "LMPC_TABLE_I"
    SECTOR_FRAMEWORK = "SECTOR_FRAMEWORK"


class WidthRatioResult(StrEnum):
    """Represent Rule 7(3) ratio applicability and deterministic comparison."""

    MEETS = "MEETS"
    DOES_NOT_MEET = "DOES_NOT_MEET"
    EXEMPT = "EXEMPT"
