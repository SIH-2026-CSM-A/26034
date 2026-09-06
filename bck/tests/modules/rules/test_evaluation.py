"""Tests for status safety, numeric concepts, and effective dates."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.contracts import DeclarationField
from app.modules.rules import (
    NumericConstraint,
    RuleDefinition,
    RuleStatus,
    Verdict,
    declarations_governed_by_rule,
    evaluate_numeric_constraint,
    evaluate_rule,
    load_rules,
    rule_governs_declaration,
    select_effective_rule,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
CORPUS_DIRECTORY = REPOSITORY_ROOT / "rules-corpus"
RULE_STORE_PATH = REPOSITORY_ROOT / "bck" / "app" / "modules" / "rules" / "data" / "rules.yaml"
ECOMMERCE_CLAUSE = "Rule 6(10A)"


def _definition(status: RuleStatus) -> RuleDefinition:
    """Build a synthetic declaration rule for central status-gate tests."""
    return RuleDefinition(
        rule_id="TEST-STATUS",
        clause_ref="Test clause",
        gazette_ref="GSR-629E__2017-06-23__amendment-rules-2017.pdf",
        source_text="Synthetic source text used only by a status test.",
        status=status,
        effective_from=date(2020, 1, 1),
        effective_to=None,
        applies_to=("test_input",),
        conditions={
            "kind": "declaration_required",
            "declarations": ["test_declaration"],
            "exceptions": [],
        },
        evidence_requirement="test_evidence",
        severity="POTENTIAL VIOLATION",
    )


@pytest.mark.parametrize(
    "proposed_verdict",
    [Verdict.PASS, Verdict.POTENTIAL_VIOLATION, Verdict.REVIEW],
)
def test_unverified_rule_always_evaluates_to_review(proposed_verdict: Verdict) -> None:
    """No proposed outcome may bypass the central UNVERIFIED review gate."""
    rule = _definition(RuleStatus.UNVERIFIED)

    assert evaluate_rule(rule, proposed_verdict) is Verdict.REVIEW


def test_verified_rule_preserves_proposed_verdict() -> None:
    """The status gate must preserve deterministic outcomes for verified rules."""
    rule = _definition(RuleStatus.VERIFIED)

    assert evaluate_rule(rule, Verdict.PASS) is Verdict.PASS
    assert evaluate_rule(rule, Verdict.POTENTIAL_VIOLATION) is Verdict.POTENTIAL_VIOLATION


def test_schema_exposes_distinct_rounding_and_tolerance_fields() -> None:
    """The temporary schema must model rounding increments and tolerances separately."""
    properties = NumericConstraint.model_json_schema()["properties"]

    assert "rounding_increment" in properties
    assert "tolerance" in properties
    assert properties["rounding_increment"] != properties["tolerance"]


def test_rounding_increment_and_tolerance_diverge_at_boundary() -> None:
    """Synthetic boundary values must demonstrate that rounding is not tolerance."""
    rounding = NumericConstraint(kind="numeric_constraint", rounding_increment=Decimal("1"))
    tolerance = NumericConstraint(kind="numeric_constraint", tolerance=Decimal("0.5"))

    assert not evaluate_numeric_constraint(
        rounding,
        declared_value=Decimal("10"),
        expected_value=Decimal("10.5"),
    )
    assert evaluate_numeric_constraint(
        tolerance,
        declared_value=Decimal("10"),
        expected_value=Decimal("10.5"),
    )


def test_numeric_constraint_requires_exactly_one_concept() -> None:
    """A numeric condition must never collapse both concepts into one comparison."""
    with pytest.raises(ValidationError):
        NumericConstraint(kind="numeric_constraint")

    with pytest.raises(ValidationError):
        NumericConstraint(
            kind="numeric_constraint",
            rounding_increment=Decimal("1"),
            tolerance=Decimal("0.5"),
        )


@pytest.mark.parametrize(
    ("evaluation_date", "expected_rule_id"),
    [
        (date(2026, 7, 1), "R6-10A-GSR-128E"),
        (date(2027, 6, 30), "R6-10A-GSR-128E"),
        (date(2027, 7, 1), "R6-10A-GSR-312E"),
        (date(2028, 1, 1), "R6-10A-GSR-312E"),
    ],
)
def test_effective_date_selects_correct_rule_6_10a_version(
    evaluation_date: date,
    expected_rule_id: str,
) -> None:
    """The 2027 substitution must not displace the 2026 rule before commencement."""
    rules = load_rules(RULE_STORE_PATH, corpus_dir=CORPUS_DIRECTORY)

    selected = select_effective_rule(rules, ECOMMERCE_CLAUSE, evaluation_date)

    assert selected is not None
    assert selected.rule_id == expected_rule_id


def test_rule_6_10a_has_no_active_version_before_2026_07_01() -> None:
    """No encoded Rule 6(10A) version may apply before its first commencement date."""
    rules = load_rules(RULE_STORE_PATH, corpus_dir=CORPUS_DIRECTORY)

    assert select_effective_rule(rules, ECOMMERCE_CLAUSE, date(2026, 6, 30)) is None


def test_evaluation_helper_filters_by_governs_declarations() -> None:
    """Filtering by governs_declarations evaluates only the specified fields."""
    rule = _definition(RuleStatus.VERIFIED).model_copy(
        update={"governs_declarations": (DeclarationField.NET_QUANTITY,)}
    )
    candidate_fields = (
        DeclarationField.NET_QUANTITY,
        DeclarationField.RETAIL_SALE_PRICE,
        DeclarationField.NAME_AND_ADDRESS,
    )

    evaluated = declarations_governed_by_rule(rule, candidate_fields)
    assert evaluated == (DeclarationField.NET_QUANTITY,)
    assert rule_governs_declaration(rule, DeclarationField.NET_QUANTITY) is True
    assert rule_governs_declaration(rule, DeclarationField.RETAIL_SALE_PRICE) is False
    assert rule_governs_declaration(rule, DeclarationField.NAME_AND_ADDRESS) is False


def test_widening_evaluation_scope_fails_falsification_check() -> None:
    """Widening evaluation scope to un-governed fields fails the boundary assertion.

    Falsification check: introduces the defect where an evaluation consumer bypasses
    governs_declarations filtering and evaluates candidate declarations indiscriminately.
    Verifies that the assertion guarding scope integrity goes red when widened.
    """
    rule = _definition(RuleStatus.VERIFIED).model_copy(
        update={"governs_declarations": (DeclarationField.NET_QUANTITY,)}
    )
    candidate_fields = (
        DeclarationField.NET_QUANTITY,
        DeclarationField.RETAIL_SALE_PRICE,
        DeclarationField.NAME_AND_ADDRESS,
    )

    # Compliant consumer filters by governs_declarations
    governed_evaluation = declarations_governed_by_rule(rule, candidate_fields)
    assert all(
        rule.governs_declarations is not None and field in rule.governs_declarations
        for field in governed_evaluation
    )

    # Defective consumer evaluates widened scope (all candidates regardless of governs_declarations)
    widened_scope = candidate_fields

    # Falsification check: invariant must fail for the widened scope
    is_strictly_governed = all(
        rule.governs_declarations is not None and field in rule.governs_declarations
        for field in widened_scope
    )
    assert not is_strictly_governed, (
        "Widening scope beyond governs_declarations must fail the invariant check"
    )

    unauthorized_fields = [f for f in widened_scope if not rule.governs(f)]
    assert unauthorized_fields == [
        DeclarationField.RETAIL_SALE_PRICE,
        DeclarationField.NAME_AND_ADDRESS,
    ]


def test_unpopulated_governs_declarations_falls_back_to_broad_evaluation() -> None:
    """None for governs_declarations evaluates all candidate declarations (broad fallback)."""
    rule = _definition(RuleStatus.VERIFIED).model_copy(update={"governs_declarations": None})
    candidates = (
        DeclarationField.NET_QUANTITY,
        DeclarationField.RETAIL_SALE_PRICE,
    )
    evaluated = declarations_governed_by_rule(rule, candidates)
    assert evaluated == candidates
    assert all(rule_governs_declaration(rule, f) for f in candidates)
