"""What the rules-to-contracts adapter promises.

Two of these are guards rather than behaviour checks.
:func:`test_every_severity_member_is_mapped` fails the day someone adds a member to
``rules.Severity``, because the alternative is a ``KeyError`` surfacing at verdict
assembly on a real scan. :func:`test_mutating_the_source_rule_cannot_reach_a_snapshot`
fails if the snapshot ever becomes a view onto the rule instead of a copy of it.
"""

from datetime import date
from decimal import Decimal

import pytest

from app.contracts import DeclarationField, RuleSeverity, RuleStatus
from app.modules.rules import RuleDefinition, load_rules
from app.modules.rules import RuleStatus as RulesRuleStatus
from app.modules.rules.models import Severity
from app.pipeline.rule_snapshot import (
    DECLARATION_FIELDS,
    SEVERITY_ROUTING,
    UnbasedToleranceError,
    UnmappedDeclarationError,
    declaration_fields,
    snapshot_from_rule,
)

RULE_SET_VERSION = "2026.09.1"
EXISTING_GAZETTE = "GSR-629E__2017-06-23__amendment-rules-2017.pdf"


def _rule(**overrides: object) -> RuleDefinition:
    """A minimal valid rules-module rule. Tests start here and override."""
    fields: dict[str, object] = {
        "rule_id": "TEST-RULE",
        "clause_ref": "Test clause",
        "gazette_ref": EXISTING_GAZETTE,
        "source_text": "Synthetic source text used only by an adapter test.",
        "status": "VERIFIED",
        "effective_from": date(2020, 1, 1),
        "effective_to": None,
        "applies_to": ("retail_packages",),
        "conditions": {
            "kind": "declaration_required",
            "declarations": ["net_quantity_or_count"],
            "exceptions": [],
        },
        "evidence_requirement": "normalized_quantity_or_count_declaration",
        "severity": "POTENTIAL_VIOLATION",
    }
    fields.update(overrides)
    return RuleDefinition(**fields)  # type: ignore[arg-type]


def _shipped_rule(rule_id: str) -> RuleDefinition:
    """One rule as actually encoded in ``app/modules/rules/data/rules.yaml``."""
    matches = [rule for rule in load_rules() if rule.rule_id == rule_id]
    assert len(matches) == 1, f"expected exactly one rule {rule_id}, found {len(matches)}"
    return matches[0]


# --- the severity table -----------------------------------------------------------------


def test_every_severity_member_is_mapped() -> None:
    """No member of the source enum may reach assembly without a routing decision.

    A missing entry is a ``KeyError`` on a live scan, not a test failure, so this asserts
    coverage of the enum rather than of the entries someone remembered to write.
    """
    unmapped = [member.name for member in Severity if member not in SEVERITY_ROUTING]
    assert not unmapped, (
        f"rules.Severity members with no contracts.RuleSeverity routing: {unmapped}. "
        "Add each one to SEVERITY_ROUTING deliberately — the two enums mean different "
        "things and there is no name or value correspondence to fall back on."
    )


def test_the_two_severity_enums_are_not_interchangeable() -> None:
    """Guards the table against being 'simplified' into a value or name conversion later.

    The disjointness is the whole claim. Before CTR-004 it also held by accident, because
    ``Severity.POTENTIAL_VIOLATION`` was spelled with a space and so matched nothing
    anywhere; asserting that spelling was asserting the accident. What must stay true is
    that no member of either enum shares a name or a value with the other.
    """
    assert {member.value for member in Severity}.isdisjoint({m.value for m in RuleSeverity})
    assert {member.name for member in Severity}.isdisjoint({m.name for m in RuleSeverity})


def test_severity_routes_to_its_documented_counterpart() -> None:
    assert SEVERITY_ROUTING[Severity.POTENTIAL_VIOLATION] is RuleSeverity.MANDATORY
    assert SEVERITY_ROUTING[Severity.REVIEW] is RuleSeverity.CONDITIONAL


def test_the_rules_module_names_the_contracts_rule_status_and_not_a_copy() -> None:
    """One class, not two that agree. The adapter passes ``rule.status`` straight through.

    Written because nothing else catches the regression. A second ``RuleStatus`` declared
    inside ``app.modules.rules`` with the same members would leave every other test in
    this suite green: ``RuleParameterSnapshot.status`` is typed to the contracts enum, and
    a ``StrEnum`` member from the duplicate arrives at validation as the string
    ``"VERIFIED"``, which pydantic coerces back into the contracts member. The two enums
    diverge only when one gains a member or changes a value, and by then the snapshot is
    raising on a real scan rather than failing here.

    Verified by reintroducing the duplicate: the full suite stayed green, and only this
    assertion goes red.
    """
    assert RulesRuleStatus is RuleStatus


# --- declaration mapping ------------------------------------------------------------------


def test_declaration_strings_resolve_to_contracts_fields() -> None:
    assert declaration_fields(_rule()) == (DeclarationField.NET_QUANTITY,)


def test_one_obligation_named_three_ways_collapses_to_one_field() -> None:
    """Rule 6(1)(a) names manufacturer, packer and importer. It is a single obligation."""
    rule = _shipped_rule("R6-1-A")
    assert len(rule.conditions.declarations) == 3  # type: ignore[union-attr]
    assert declaration_fields(rule) == (DeclarationField.NAME_AND_ADDRESS,)


def test_a_rule_with_no_declaration_condition_names_no_fields() -> None:
    """A Table-I height band requires no declaration of its own. Absence, not failure."""
    assert declaration_fields(_shipped_rule("R7-2-TABLE-I")) == ()


def test_an_unmapped_declaration_raises_rather_than_being_dropped() -> None:
    """A silently dropped declaration is a finding that never gets made."""
    rule = _rule(
        conditions={
            "kind": "declaration_required",
            "declarations": ["a_declaration_nobody_has_mapped"],
            "exceptions": [],
        }
    )
    with pytest.raises(UnmappedDeclarationError, match="a_declaration_nobody_has_mapped"):
        declaration_fields(rule)
    with pytest.raises(UnmappedDeclarationError):
        snapshot_from_rule(rule, RULE_SET_VERSION)


def test_every_declaration_in_the_shipped_rule_store_is_mapped() -> None:
    """The rule store and the map must not drift apart unnoticed."""
    for rule in load_rules():
        declaration_fields(rule)


# --- tolerance ------------------------------------------------------------------------------


def test_a_rounding_increment_is_lifted_onto_its_own_field() -> None:
    """An increment transforms a value in steps and needs no basis to be read by."""
    rule = _rule(conditions={"kind": "numeric_constraint", "rounding_increment": Decimal("0.05")})
    snapshot = snapshot_from_rule(rule, RULE_SET_VERSION)
    assert snapshot.rounding_increment == Decimal("0.05")
    assert snapshot.tolerance is None
    assert snapshot.tolerance_basis is None


def test_a_tolerance_with_no_basis_is_refused() -> None:
    """Five paise or five percent. The rule must be re-encoded, not copied through."""
    rule = _rule(conditions={"kind": "numeric_constraint", "tolerance": Decimal("0.05")})
    with pytest.raises(UnbasedToleranceError, match="no basis"):
        snapshot_from_rule(rule, RULE_SET_VERSION)


# --- round trip against the real rule store ---------------------------------------------------


def test_a_shipped_declaration_rule_round_trips_with_its_gazette() -> None:
    rule = _shipped_rule("R6-1-A")
    snapshot = snapshot_from_rule(rule, RULE_SET_VERSION)

    assert snapshot.gazette_ref == rule.gazette_ref
    assert snapshot.gazette_ref.endswith(".pdf")
    assert snapshot.rule_set_version == RULE_SET_VERSION
    assert snapshot.rule_id == "R6-1-A"
    assert snapshot.clause_ref == "Rule 6(1)(a)"
    assert snapshot.source_text == rule.source_text
    assert snapshot.status is RuleStatus.VERIFIED
    assert snapshot.severity is RuleSeverity.MANDATORY
    assert snapshot.parameters["conditions"]["kind"] == "declaration_required"
    assert snapshot.parameters["applies_to"] == list(rule.applies_to)
    assert snapshot.parameters["evidence_requirement"] == rule.evidence_requirement
    assert snapshot.parameters["declaration_fields"] == ["NAME_AND_ADDRESS"]


def test_a_decimal_heavy_rule_round_trips_as_json_safe_parameters() -> None:
    """Table-I bands are ``Decimal``, which is not a ``JsonValue``.

    A plain ``model_dump()`` would fail validation on the way into ``parameters``, so the
    band figures have to arrive as strings and stay exact.
    """
    rule = _shipped_rule("R7-2-TABLE-I")
    snapshot = snapshot_from_rule(rule, RULE_SET_VERSION)

    assert snapshot.gazette_ref == "GSR-629E__2017-06-23__amendment-rules-2017.pdf"
    bands = snapshot.parameters["conditions"]["bands"]
    assert len(bands) == 5
    assert bands[0]["maximum_area_inclusive_cm2"] == "50"
    assert bands[0]["normal_minimum_height_mm"] == "1.0"
    assert Decimal(bands[0]["normal_minimum_height_mm"]) == Decimal("1.0")


def test_every_shipped_rule_snapshots_with_a_gazette_reference() -> None:
    """A snapshot nobody can trace back to a gazette is not evidence."""
    for rule in load_rules():
        snapshot = snapshot_from_rule(rule, RULE_SET_VERSION)
        assert snapshot.gazette_ref == rule.gazette_ref
        assert snapshot.gazette_ref.strip()
        assert snapshot.rule_set_version == RULE_SET_VERSION


# --- the snapshot is a copy --------------------------------------------------------------------


def test_amending_the_source_rule_cannot_reach_a_snapshot() -> None:
    """The failure the whole snapshot design exists to prevent.

    An amendment landing on Tuesday must not change what Monday's scan is recorded as
    having found, and the officer who signed Monday's finding must not have it move
    underneath them.

    Amendment, not in-place mutation: a rules ``RuleDefinition`` is frozen and holds only
    tuples, so there is no in-place edit to attempt. ``model_copy`` is how an amendment
    actually arrives.
    """
    rule = _shipped_rule("R6-1-A")
    snapshot = snapshot_from_rule(rule, RULE_SET_VERSION)
    original = snapshot.parameters["conditions"]["declarations"][0]

    amended = rule.model_copy(
        update={
            "source_text": "amended text",
            "evidence_requirement": "something_else",
            "applies_to": ("nothing_at_all",),
        }
    )

    assert amended.source_text == "amended text"
    assert snapshot.source_text == rule.source_text
    assert snapshot.parameters["evidence_requirement"] == rule.evidence_requirement
    assert snapshot.parameters["applies_to"] == list(rule.applies_to)
    assert snapshot.parameters["conditions"]["declarations"][0] == original


def test_editing_one_snapshots_parameters_cannot_reach_the_next() -> None:
    """Snapshots are independent of each other and of the rule they came from.

    ``parameters`` is a plain mutable dict on a frozen model, so a caller *can* edit one.
    What must not happen is that edit surfacing in the rule or in a snapshot taken later.
    """
    rule = _shipped_rule("R6-1-A")
    first = snapshot_from_rule(rule, RULE_SET_VERSION)

    first.parameters["conditions"]["declarations"][0] = "mutated in place"
    first.parameters["applies_to"].append("mutated")
    first.parameters["injected"] = "mutated"

    second = snapshot_from_rule(rule, RULE_SET_VERSION)
    assert second.parameters["conditions"]["declarations"][0] == "manufacturer_name_and_address"
    assert second.parameters["applies_to"] == list(rule.applies_to)
    assert "injected" not in second.parameters


def test_the_map_covers_only_strings_the_rule_store_uses() -> None:
    """Every mapped string is reachable from the shipped store — no speculative entries."""
    encoded = {
        declaration
        for rule in load_rules()
        if hasattr(rule.conditions, "declarations")
        for declaration in rule.conditions.declarations  # type: ignore[union-attr]
    }
    assert encoded <= set(DECLARATION_FIELDS)
    assert set(DECLARATION_FIELDS) == encoded
