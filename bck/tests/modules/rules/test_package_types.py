"""Tests for the Combination Package and Group Package definitions, G.S.R. 722(E)."""

from datetime import date

import pytest

from app.modules.rules import ConstituentSimilarity, PackageType, Severity, rule_by_id

GSR_722E = "GSR-722E__2023-10-06__amendment-rules-2023.pdf"


@pytest.mark.parametrize(
    ("rule_id", "clause_ref", "package_type", "similarity"),
    [
        (
            "R2-KA-COMBINATION-PACKAGE",
            "Rule 2(ka)",
            PackageType.COMBINATION_PACKAGE,
            ConstituentSimilarity.DISSIMILAR,
        ),
        (
            "R2-KB-GROUP-PACKAGE",
            "Rule 2(kb)",
            PackageType.GROUP_PACKAGE,
            ConstituentSimilarity.SIMILAR_BUT_NOT_IDENTICAL,
        ),
    ],
)
def test_each_package_definition_loads_with_its_gazette_reference(
    rule_id: str,
    clause_ref: str,
    package_type: PackageType,
    similarity: ConstituentSimilarity,
) -> None:
    """Both definitions trace to G.S.R. 722(E) by filename, and came into force 01.01.2024."""
    rule = rule_by_id(rule_id)

    assert rule.gazette_ref == GSR_722E
    assert rule.clause_ref == clause_ref
    assert rule.effective_from == date(2024, 1, 1)
    assert rule.effective_to is None

    condition = rule.conditions
    assert condition.kind == "package_definition"
    assert condition.package_type is package_type
    assert condition.constituent_similarity is similarity
    assert condition.intended_for_retail_sale is True
    assert condition.minimum_constituent_count == 2
    assert condition.illustrations


def test_the_two_definitions_differ_only_in_constituent_similarity() -> None:
    """Dissimilar against similar-but-not-identical is the whole distinction."""
    combination = rule_by_id("R2-KA-COMBINATION-PACKAGE").conditions
    group = rule_by_id("R2-KB-GROUP-PACKAGE").conditions

    assert combination.constituent_similarity is not group.constituent_similarity
    assert combination.minimum_constituent_count == group.minimum_constituent_count
    assert combination.intended_for_retail_sale == group.intended_for_retail_sale


@pytest.mark.parametrize("rule_id", ["R2-KA-COMBINATION-PACKAGE", "R2-KB-GROUP-PACKAGE"])
def test_a_definition_proposes_review_not_a_violation(rule_id: str) -> None:
    """A definition classifies a package; failing to be one is not a finding."""
    assert rule_by_id(rule_id).severity is Severity.REVIEW
