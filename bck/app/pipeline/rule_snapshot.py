"""Adapt the rules module's internal rule shape into a contracts snapshot.

``app.modules.rules`` models a rule richly: a discriminated ``RuleCondition`` union whose
variants each know their own shape, a single ``evidence_requirement`` string, and an
outcome-flavoured ``Severity``. ``app.contracts`` models the same rule flatly: a generic
``parameters`` mapping, a ``DeclarationField`` vocabulary, and a routing-flavoured
``RuleSeverity``. Both are right for their own purpose — nothing outside ``rules`` ever
introspects a condition's *shape*, only that a snapshot of it exists — so this is a
translation between two deliberate designs, not a sign that either should change.

This module is that translation and the only place it happens. ``app.pipeline`` is the
only package permitted to import from ``app.modules``; the rules module knows nothing
about contracts and must not learn.

Everything a reviewer needs to re-derive a finding is copied by value. A verdict may be
read years after the rule set that produced it was republished, so ``applies_to`` and
``evidence_requirement`` travel into ``parameters`` alongside the condition dump — a
record that cannot be re-derived from itself is the failure snapshotting exists to
prevent.
"""

from copy import deepcopy
from decimal import Decimal

from pydantic import JsonValue

from app.contracts import (
    DeclarationField,
    RuleParameterSnapshot,
    RuleSeverity,
    RuleStatus,
)
from app.modules.rules import NumericConstraint, RuleDefinition

# ``Severity`` and ``DeclarationRequiredCondition`` are not on the rules package's public
# surface, and that package is single-owner — reaching into ``models`` is the only way to
# name them without editing someone else's module.
from app.modules.rules.models import DeclarationRequiredCondition, Severity


class UnmappedDeclarationError(LookupError):
    """A rule names a declaration this adapter cannot resolve to a ``DeclarationField``.

    Raised rather than skipped. A dropped declaration is a finding that silently never
    gets made, which reads downstream as a package with nothing wrong with it.
    """


class UnbasedToleranceError(ValueError):
    """A ``NumericConstraint`` carries a tolerance with no basis to read it by.

    ``Decimal("0.05")`` alone is five paise or five percent — the First Schedule states
    maximum permissible error as a percentage of declared quantity while a money
    tolerance is an absolute amount. ``contracts.RuleDefinition`` refuses to construct
    without ``tolerance_basis`` for exactly this reason, and ``rules.NumericConstraint``
    has no field to carry one. Copying the bare figure into a snapshot would rebuild that
    ambiguity one layer down, where nothing checks it. The rule must be re-encoded with a
    basis instead.
    """


SEVERITY_ROUTING: dict[Severity, RuleSeverity] = {
    Severity.POTENTIAL_VIOLATION: RuleSeverity.MANDATORY,
    Severity.REVIEW: RuleSeverity.CONDITIONAL,
}
"""``rules.Severity`` to ``contracts.RuleSeverity``. **The two enums mean different things.**

``rules.Severity`` answers *what outcome a verified rule proposes when its condition is
not met* — the evaluator's own two-way branch, REVIEW or POTENTIAL VIOLATION.
``contracts.RuleSeverity`` answers *how strong the underlying obligation is*, which is
what decides how a breach routes in the officer workflow: MANDATORY, CONDITIONAL or
ADVISORY. One is about an outcome, the other about an obligation, and they are related
only because an unconditional obligation is the kind whose breach can propose a
POTENTIAL_VIOLATION.

So this is a lookup table and not a rename. Member names do not correspond, member
counts do not match, and the values do not either — ``Severity.POTENTIAL_VIOLATION`` is
the string ``"POTENTIAL VIOLATION"`` with a space, so a value-based conversion would
raise. ``RuleSeverity.ADVISORY`` is absent from the range on purpose: guidance with no
standalone obligation behind it is not something the rule store can currently express,
and inventing a source member to reach it would be inventing law.
"""

DECLARATION_FIELDS: dict[str, DeclarationField] = {
    "manufacturer_name_and_address": DeclarationField.NAME_AND_ADDRESS,
    "packer_name_and_address_when_manufacturer_is_not_packer": (DeclarationField.NAME_AND_ADDRESS),
    "importer_name_and_address_for_imported_package": DeclarationField.NAME_AND_ADDRESS,
    "country_of_origin_or_manufacture_or_assembly": DeclarationField.COUNTRY_OF_ORIGIN,
    "common_or_generic_name": DeclarationField.COMMON_OR_GENERIC_NAME,
    "each_product_name_and_number_or_quantity_for_packages_with_more_than_one_product": (
        DeclarationField.COMMON_OR_GENERIC_NAME
    ),
    "net_quantity_or_count": DeclarationField.NET_QUANTITY,
    "month_and_year_of_manufacture": DeclarationField.MANUFACTURE_DATE,
    "visible_and_clearly_legible_month_and_year_of_manufacture": (
        DeclarationField.MANUFACTURE_DATE
    ),
    "best_before_or_use_by_date_month_and_year": DeclarationField.BEST_BEFORE_DATE,
    "retail_sale_price": DeclarationField.RETAIL_SALE_PRICE,
    "relevant_dimensions": DeclarationField.DIMENSIONS,
    "other_matter_specified_in_these_rules": DeclarationField.OTHER_PRESCRIBED_MATTER,
}
"""Declaration strings as the rule store writes them, to the obligation each answers.

Several strings share one field, and that is the point: Rule 6(1)(a) names manufacturer,
packer and importer separately in its own text but is one obligation, so all three
resolve to :attr:`~app.contracts.DeclarationField.NAME_AND_ADDRESS` rather than becoming
three findings an officer has to reconcile.

Keyed off the strings actually encoded in ``app/modules/rules/data/rules.yaml``. A rule
naming anything else raises :class:`UnmappedDeclarationError` — the map grows when the
rule store does, deliberately and in a reviewed change.
"""


def declaration_fields(rule: RuleDefinition) -> tuple[DeclarationField, ...]:
    """The declarations ``rule`` requires, resolved to contracts members.

    Empty for a rule whose condition is not a declaration requirement — a Table-I height
    band requires no declaration of its own. That is an absence, not a failure.

    Order follows the rule, duplicates are collapsed: three limbs of Rule 6(1)(a) name
    one obligation once.
    """
    condition = rule.conditions
    if not isinstance(condition, DeclarationRequiredCondition):
        return ()

    resolved: list[DeclarationField] = []
    for declaration in condition.declarations:
        try:
            resolved.append(DECLARATION_FIELDS[declaration])
        except KeyError:
            raise UnmappedDeclarationError(
                f"rule {rule.rule_id} names declaration {declaration!r}, which maps to no "
                f"DeclarationField; add it to DECLARATION_FIELDS rather than letting the "
                f"finding be dropped"
            ) from None
    return tuple(dict.fromkeys(resolved))


def _rounding_increment(rule: RuleDefinition) -> Decimal | None:
    """Lift a rounding increment off a numeric condition, refusing a basisless tolerance.

    ``rules.NumericConstraint`` requires exactly one of the two, so a constraint that is
    not a tolerance is an increment. An increment needs no basis — it transforms a value
    in steps, in the field's own unit.
    """
    condition = rule.conditions
    if not isinstance(condition, NumericConstraint):
        return None
    if condition.tolerance is not None:
        raise UnbasedToleranceError(
            f"rule {rule.rule_id} carries tolerance {condition.tolerance} with no basis; "
            f"re-encode it stating whether the figure is absolute or a percentage"
        )
    return condition.rounding_increment


def _parameters(rule: RuleDefinition, fields: tuple[DeclarationField, ...]) -> dict[str, JsonValue]:
    """Everything about the rule that has no dedicated column on the snapshot.

    ``mode="json"`` is load-bearing rather than stylistic: Table-I bands, ratio thresholds
    and PDP multipliers are all ``Decimal``, and ``Decimal`` is not a ``JsonValue``. A
    plain ``model_dump()`` fails validation on the way into ``parameters``.
    """
    return {
        "conditions": rule.conditions.model_dump(mode="json"),
        "applies_to": list(rule.applies_to),
        "evidence_requirement": rule.evidence_requirement,
        "declaration_fields": [field.value for field in fields],
    }


def snapshot_from_rule(rule: RuleDefinition, rule_set_version: str) -> RuleParameterSnapshot:
    """Copy ``rule`` into the snapshot a finding carries, by value.

    ``rule`` is an ``app.modules.rules`` :class:`RuleDefinition`, not the contracts type
    of the same name.

    The result shares no state with ``rule``. A verdict records what the rule said when it
    was issued, and an amendment landing on Tuesday must not change what Monday's scan is
    recorded as having found.

    Today that holds for two independent reasons: a rules ``RuleDefinition`` is frozen all
    the way down — its ``applies_to`` and every condition's collections are tuples — so it
    cannot be mutated in place at all, and ``_parameters`` builds fresh containers rather
    than handing back anything the rule holds. The ``deepcopy`` below is therefore
    belt-and-braces rather than load-bearing, and no test can currently be made to fail by
    removing it. It stays because ``parameters`` is typed ``dict[str, JsonValue]``, which
    permits nested mutable containers, and the guarantee should not quietly depend on
    ``_parameters`` never growing a branch that passes one through.

    ``gazette_ref`` and ``rule_set_version`` are both required and always present: a
    snapshot nobody can trace back to a gazette and a published set is not evidence.
    """
    return RuleParameterSnapshot(
        rule_id=rule.rule_id,
        clause_ref=rule.clause_ref,
        gazette_ref=rule.gazette_ref,
        source_text=rule.source_text,
        # Members and values coincide across the two RuleStatus enums today. Converting
        # through the value states that dependency instead of assuming the objects are
        # interchangeable, and raises the day one of them gains a member.
        status=RuleStatus(rule.status.value),
        severity=SEVERITY_ROUTING[rule.severity],
        rule_set_version=rule_set_version,
        parameters=deepcopy(_parameters(rule, declaration_fields(rule))),
        rounding_increment=_rounding_increment(rule),
        tolerance=None,
        tolerance_basis=None,
    )
