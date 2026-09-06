"""Tests for the package definitions inserted by G.S.R. 722(E): 2(ka), 2(kb) and 2(kc)."""

from datetime import date

import pytest

from app.modules.rules import (
    ConstituentSimilarity,
    PackageType,
    Severity,
    load_rules,
    rule_by_id,
)

GSR_722E = "GSR-722E__2023-10-06__amendment-rules-2023.pdf"
DEFINITION_RULE_IDS = [
    "R2-KA-COMBINATION-PACKAGE",
    "R2-KB-GROUP-PACKAGE",
    "R2-KC-MULTI-PIECE-PACKAGE",
]


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
        (
            "R2-KC-MULTI-PIECE-PACKAGE",
            "Rule 2(kc)",
            PackageType.MULTI_PIECE_PACKAGE,
            ConstituentSimilarity.IDENTICAL,
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


def test_the_three_definitions_are_mutually_exclusive() -> None:
    """One axis, three values, so no package can satisfy two definitions at once."""
    conditions = [rule_by_id(rule_id).conditions for rule_id in DEFINITION_RULE_IDS]

    assert len({condition.package_type for condition in conditions}) == 3
    assert len({condition.constituent_similarity for condition in conditions}) == 3
    assert {condition.minimum_constituent_count for condition in conditions} == {2}
    assert {condition.intended_for_retail_sale for condition in conditions} == {True}


def test_a_multi_piece_package_is_not_a_group_or_combination_package() -> None:
    """The distinction is per-piece labelling and per-piece saleability, from 2(kc).

    A group package is "similar, but not identical" commodities sold as a package. A
    multi-piece package is the *same* commodity in *identical* quantity, in pieces that
    are individually packaged or labelled and may be sold on their own. Reading one as
    the other would put the wrong obligations on the inner pieces.
    """
    multi_piece = rule_by_id("R2-KC-MULTI-PIECE-PACKAGE").conditions
    group = rule_by_id("R2-KB-GROUP-PACKAGE").conditions
    combination = rule_by_id("R2-KA-COMBINATION-PACKAGE").conditions

    assert multi_piece.constituent_similarity is ConstituentSimilarity.IDENTICAL
    assert group.constituent_similarity is ConstituentSimilarity.SIMILAR_BUT_NOT_IDENTICAL
    assert combination.constituent_similarity is ConstituentSimilarity.DISSIMILAR

    assert multi_piece.constituents_individually_packaged_or_labelled is True
    assert multi_piece.retail_sale_of_individual_pieces_permitted is True

    for other in (group, combination):
        assert other.constituents_individually_packaged_or_labelled is False
        assert other.retail_sale_of_individual_pieces_permitted is False


def test_the_gazette_states_no_multi_piece_outer_wrapper_rule() -> None:
    """G.S.R. 722(E) does not amend Rule 9, so no interaction is encoded.

    Rule 9(3) applies generally to any package with an outside container. There is no
    multi-piece variant of it in the corpus, and inventing one would be a rule with no
    gazette behind it.
    """
    outer_container_rules = [
        rule for rule in load_rules() if rule.conditions.kind == "outer_container"
    ]

    assert [rule.rule_id for rule in outer_container_rules] == ["R9-3-OUTER-CONTAINER"]
    assert outer_container_rules[0].gazette_ref.startswith("LMPC-2011")


@pytest.mark.parametrize("rule_id", DEFINITION_RULE_IDS)
def test_a_definition_proposes_review_not_a_violation(rule_id: str) -> None:
    """A definition classifies a package; failing to be one is not a finding."""
    assert rule_by_id(rule_id).severity is Severity.REVIEW
