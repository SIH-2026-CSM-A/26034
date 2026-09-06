"""Shared vocabulary for the rule store: value constraints and closed enumerations.

Imports nothing from this package — only from ``app.contracts``, which is below every
module — so the schema files below it can depend on it in one direction and no other.
Splitting it out is what the 300-line limit bought — the rule store grew a placement
rule, a manner rule, two package definitions and a sector dispatch in RUL-002, and one
file could no longer hold the schema and stay readable.
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

# Re-exports, not imports this file uses. Both are defined in app.contracts and aliased
# here so the schema files below can keep importing them from one place. The redundant
# alias is what marks each as public and keeps ruff from removing it as unused; deleting
# either line breaks files in this package.
#
# ProductCategory lives in contracts because extraction proposes a category and may not
# import this module — one definition, because sector_overrides keys on it and a drifting
# second copy would confirm a category that routes to nothing.
#
# RuleStatus lives in contracts because a verdict record carries it: a finding states
# whether the rule behind it was confirmed against its gazette, so the value crosses the
# module boundary and must not be spelled twice. This module had its own copy with
# identical members until CTR-004; two enums with the same members and the same values
# are one amendment away from disagreeing, and nothing would have caught the day they did.
from app.contracts import ProductCategory as ProductCategory
from app.contracts import RuleStatus as RuleStatus

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
PositiveDecimal = Annotated[Decimal, Field(gt=0)]
NonNegativeDecimal = Annotated[Decimal, Field(ge=0)]


class StrictRuleModel(BaseModel):
    """Reject fields outside each declared rule-store schema."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class Verdict(StrEnum):
    """Represent decision-support outcomes without making legal determinations."""

    PASS = "PASS"
    REVIEW = "REVIEW"
    POTENTIAL_VIOLATION = "POTENTIAL_VIOLATION"


class Severity(StrEnum):
    """Represent the outcome used when a verified rule condition is not met."""

    REVIEW = "REVIEW"
    POTENTIAL_VIOLATION = "POTENTIAL_VIOLATION"


class OverrideTarget(StrEnum):
    """Identify which obligation a sector override moves to another framework.

    ``PDP_DECLARATION`` is Rule 2(h), ``MANUFACTURER_DECLARATION`` is Rule 6(1)(a) and
    ``DATE_DECLARATION`` is Rule 6(1)(d); ``TABLE_HEIGHT`` and ``WIDTH_RATIO`` are Rule
    7(2) and Rule 7(3).

    ``PACKAGE_DEFINITION`` routes what a package *is* rather than what it must declare —
    the shape the proviso to Rule 2(kc) takes, and the same shape as Rule 2(k)'s existing
    proviso handing "retail food package" to the Food Safety and Standards Act, 2006.
    """

    TABLE_HEIGHT = "table_height"
    WIDTH_RATIO = "width_ratio"
    PDP_DECLARATION = "pdp_declaration"
    MANUFACTURER_DECLARATION = "manufacturer_declaration"
    DATE_DECLARATION = "date_declaration"
    PACKAGE_DEFINITION = "package_definition"


class PackageType(StrEnum):
    """Identify a package composition the rules define rather than measure."""

    COMBINATION_PACKAGE = "combination_package"
    GROUP_PACKAGE = "group_package"
    MULTI_PIECE_PACKAGE = "multi_piece_package"


class ConstituentSimilarity(StrEnum):
    """Distinguish the three package definitions inserted by G.S.R. 722(E).

    One axis, three mutually exclusive values, so a package cannot satisfy two of the
    definitions at once. Rule 2(ka) is dissimilar commodities, Rule 2(kb) is similar but
    not identical, and Rule 2(kc) is the same commodities of identical quantity.
    """

    DISSIMILAR = "dissimilar"
    SIMILAR_BUT_NOT_IDENTICAL = "similar_but_not_identical"
    IDENTICAL = "identical"


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
