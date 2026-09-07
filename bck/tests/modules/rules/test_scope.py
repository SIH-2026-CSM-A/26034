"""Tests for Rule 3 — whether Chapter II reaches a package at all.

The load-bearing claims: an exclusion has to be *established* and is never inferred from
an absence; the thresholds come from the store rather than from Python; and an indicated
but unconfirmed exclusion routes to an officer instead of resolving either way.

Every threshold assertion here is falsifiable by editing the figure in ``data/rules.yaml``,
which is the point — a test that hardcodes 25 would pass against a store that had lost it.
"""

from decimal import Decimal

import pytest

from app.contracts import DeclarationField, NormalisedField
from app.modules.rules import (
    ScopeStatus,
    chapter_ii_scope,
    not_for_retail_sale_declared,
    rule_3b_is_subsumed_by_rule_3a,
    rule_by_id,
)
from app.modules.rules.scope import CHAPTER_SCOPE_RULE_ID


def quantity(value: str, unit: str) -> NormalisedField:
    """One declared net quantity, canonicalised the way the pipeline canonicalises it."""
    return NormalisedField(
        field_type=DeclarationField.NET_QUANTITY,
        span_refs=("span-1",),
        normalised_value=f"{value} {unit}",
        numeric_value=Decimal(value),
        unit=unit,
        parse_confidence=1.0,
    )


def unreadable() -> NormalisedField:
    """A net quantity present on the pack but not canonicalised into a figure."""
    return NormalisedField(
        field_type=DeclarationField.NET_QUANTITY,
        span_refs=("span-1",),
        normalised_value="NET WT. ~~~",
        parse_confidence=0.0,
    )


def condition():
    """The stored Rule 3 parameters."""
    return rule_by_id(CHAPTER_SCOPE_RULE_ID).conditions


# Verbatim from the corpus, as literals. These must NOT be read from the store: a test that
# fetches a figure and then feeds it back compares the store against itself and passes
# whatever the store holds. The first draft of this file did exactly that for the marker
# phrase and for the weight threshold, and both survived a deliberate edit to rules.yaml.
#
# Rule 3: "(a) packages of commodities containing quantity of more than 25 kilogram or 25
# litre; (b) cement, fertilizer and agricultural farm produce sold in bags above 50
# kilogram". Rule 2(bb) and 2(bc) as substituted: "the package shall have declaration
# ' not for retail sale' ".
CORPUS_WEIGHT_KG = Decimal(25)
CORPUS_VOLUME_L = Decimal(25)
CORPUS_BAGGED_KG = Decimal(50)
CORPUS_MARKER = "not for retail sale"


# --- Rule 3(a): deterministic from the declared net quantity, no officer involved --------


def test_rule_3a_boundary_is_exclusive_at_the_stored_threshold() -> None:
    """ "More than 25 kilogram" — so 25 kilogram exactly is still inside Chapter II.

    The boundary is the whole of this limb. A ``>=`` here would put every 25 kg sack out
    of scope and produce NOT_APPLICABLE on a package that owes every Rule 6 declaration.
    """
    threshold = condition().maximum_weight_inclusive_kg

    at = chapter_ii_scope(net_quantity=(quantity(str(threshold), "kg"),))
    assert at.status is ScopeStatus.GOVERNED

    just_above = chapter_ii_scope(net_quantity=(quantity(str(threshold + Decimal("0.001")), "kg"),))
    assert just_above.status is ScopeStatus.EXCLUDED
    assert just_above.limb == "Rule 3(a)"


def test_the_store_carries_the_figures_rule_3_actually_states() -> None:
    """Every threshold this module decides on, pinned to the gazette text as a literal.

    Falsified by any edit to those figures in ``data/rules.yaml``. This is the test that
    makes the rest of the file mean something: they compare behaviour against the store,
    and this is what stops the store drifting away from the corpus underneath them.
    """
    parameters = condition()
    assert parameters.maximum_weight_inclusive_kg == CORPUS_WEIGHT_KG
    assert parameters.maximum_volume_inclusive_l == CORPUS_VOLUME_L
    assert parameters.bagged_maximum_inclusive_kg == CORPUS_BAGGED_KG
    assert parameters.not_for_retail_sale_marker == CORPUS_MARKER


def test_the_reason_quotes_the_threshold_the_decision_used() -> None:
    """An officer reading the finding gets the figure, not a bare conclusion."""
    decision = chapter_ii_scope(net_quantity=(quantity("30", "kg"),))
    assert str(CORPUS_WEIGHT_KG) in decision.reason


def test_rule_3a_converts_grams_and_millilitres_to_the_stored_units() -> None:
    """A 30000 g sack is a 30 kg sack. Rule 3(a) states kilogram and litre."""
    assert chapter_ii_scope(net_quantity=(quantity("30000", "g"),)).status is ScopeStatus.EXCLUDED
    assert chapter_ii_scope(net_quantity=(quantity("30000", "ml"),)).status is ScopeStatus.EXCLUDED
    assert chapter_ii_scope(net_quantity=(quantity("25000", "g"),)).status is ScopeStatus.GOVERNED
    assert chapter_ii_scope(net_quantity=(quantity("25000", "ml"),)).status is ScopeStatus.GOVERNED


def test_rule_3a_volume_uses_the_volume_threshold_not_the_weight_one() -> None:
    """Two thresholds, two units. Comparing litres against the kilogram figure would pass
    today only because both read 25, and would diverge silently the day one is amended."""
    assert chapter_ii_scope(net_quantity=(quantity("26", "l"),)).status is ScopeStatus.EXCLUDED
    assert chapter_ii_scope(net_quantity=(quantity("24", "l"),)).status is ScopeStatus.GOVERNED


@pytest.mark.parametrize("unit", ["N", "pcs"])
def test_rule_3a_ignores_count_declarations(unit: str) -> None:
    """``N`` and ``pcs`` are counts, not newtons and not mass.

    Rule 3(a) states its threshold in "kilogram or litre". A count of 500 is not 500 of
    either, and treating it as one would exclude a box of 500 sachets from Chapter II.
    """
    assert chapter_ii_scope(net_quantity=(quantity("500", unit),)).status is ScopeStatus.GOVERNED


def test_rule_3a_straddling_declarations_go_to_an_officer() -> None:
    """A multi-piece pack declaring a per-piece and a total quantity that disagree.

    Which one Rule 3(a) is read against is not settled by the label, so neither is picked.
    """
    decision = chapter_ii_scope(net_quantity=(quantity("20", "kg"), quantity("30", "kg")))
    assert decision.status is ScopeStatus.UNCERTAIN
    assert decision.status is not ScopeStatus.EXCLUDED


def test_rule_3a_needs_every_comparable_quantity_beyond_the_threshold() -> None:
    """Two quantities that agree exclude; a count alongside them does not dilute them."""
    decision = chapter_ii_scope(
        net_quantity=(quantity("30", "kg"), quantity("30000", "g"), quantity("12", "pcs"))
    )
    assert decision.status is ScopeStatus.EXCLUDED


def test_an_unreadable_quantity_establishes_no_exclusion() -> None:
    """Retail is the default; Rule 3 is the exception, and the burden is on the exception.

    Suspending Chapter II whenever a quantity is illegible would make every poor
    photograph a verdict that says nothing about the package.
    """
    assert chapter_ii_scope(net_quantity=(unreadable(),)).status is ScopeStatus.GOVERNED
    assert chapter_ii_scope(net_quantity=()).status is ScopeStatus.GOVERNED


# --- Rule 3(b): recorded, and subsumed ---------------------------------------------------


def test_rule_3b_is_subsumed_by_rule_3a() -> None:
    """Why no Rule 3(b) branch exists, checked against the store rather than asserted.

    Rule 3(b) excludes cement, fertilizer and agricultural farm produce in bags above 50
    kilogram; Rule 3(a) excludes any quantity above 25. The first set is inside the second,
    so confirming 3(b) could never change an answer 3(a) has not already given, and an
    officer-confirmation path for it would be a branch that can never fire.

    Falsified by raising ``maximum_weight_inclusive_kg`` above ``bagged_maximum_inclusive_kg``
    in ``data/rules.yaml`` — which is precisely the amendment that would make Rule 3(b)
    operative and require that input to be built.
    """
    assert rule_3b_is_subsumed_by_rule_3a()

    parameters = condition()
    bagged = parameters.bagged_maximum_inclusive_kg + Decimal("0.001")
    decision = chapter_ii_scope(net_quantity=(quantity(str(bagged), "kg"),))
    assert decision.status is ScopeStatus.EXCLUDED
    assert decision.limb == "Rule 3(a)"


def test_rule_3b_commodities_are_recorded_verbatim() -> None:
    """The store carries the whole of Rule 3, including the limb nothing consults."""
    assert condition().bagged_commodities == (
        "cement",
        "fertilizer",
        "agricultural_farm_produce",
    )


# --- Rule 3(c): indicated by the label, confirmed only by an officer ----------------------


def test_the_matcher_finds_the_phrase_the_rules_require() -> None:
    """Matched against the corpus literal, never against whatever the store happens to hold.

    Falsified two ways, which is why both halves are here: a same-length edit to
    ``not_for_retail_sale_marker`` in the store breaks the first assertion, and dropping the
    case-folding or whitespace collapse from the matcher breaks the second.
    """
    assert condition().not_for_retail_sale_marker == CORPUS_MARKER
    assert not_for_retail_sale_declared([f"  {CORPUS_MARKER.upper()}  "])
    assert not_for_retail_sale_declared(["Net wt 500g", f"{CORPUS_MARKER} — bulk supply"])
    assert not not_for_retail_sale_declared(["Net wt 500g", "MRP Rs. 45"])


def test_the_marker_routes_to_an_officer_and_never_excludes_on_its_own() -> None:
    """A printed mark is a declaration by the packer, not proof of how it was supplied.

    Rule 3(c) turns on the package being "meant for" an industrial or institutional
    consumer. The marker evidences that and does not establish it, so the honest answer is
    UNCERTAIN — never EXCLUDED, which would drop the obligations on a packer's say-so.
    """
    decision = chapter_ii_scope(not_for_retail_sale_observed=True)
    assert decision.status is ScopeStatus.UNCERTAIN
    assert decision.status is not ScopeStatus.EXCLUDED
    assert decision.limb == "Rule 3(c)"


def test_an_officer_confirmation_excludes_where_the_marker_alone_did_not() -> None:
    """The confirmation is what Rule 3(c) needs, and it outranks everything else."""
    decision = chapter_ii_scope(institutional_or_industrial_confirmed=True)
    assert decision.status is ScopeStatus.EXCLUDED
    assert decision.limb == "Rule 3(c)"


def test_a_confirmed_exclusion_outranks_a_governed_quantity() -> None:
    """A 500 g catering sachet is confirmed out of scope by the officer, not by its size."""
    decision = chapter_ii_scope(
        net_quantity=(quantity("500", "g"),),
        institutional_or_industrial_confirmed=True,
    )
    assert decision.status is ScopeStatus.EXCLUDED


# --- the default: nothing established, nothing changed -----------------------------------


def test_absence_of_every_signal_leaves_the_package_governed() -> None:
    """The property the rest of the suite depends on.

    A package with a readable in-scope quantity, no marker and no confirmation must come
    back GOVERNED, which produces no scope findings at all. Nothing is inferred from an
    absence in either direction.
    """
    decision = chapter_ii_scope(
        net_quantity=(quantity("500", "g"),),
        not_for_retail_sale_observed=False,
        institutional_or_industrial_confirmed=False,
    )
    assert decision.status is ScopeStatus.GOVERNED
    assert decision.limb is None


def test_the_decision_names_the_rule_that_made_it() -> None:
    """An officer asked why a sack bore no findings gets the clause, not an assertion."""
    for decision in (
        chapter_ii_scope(net_quantity=(quantity("30", "kg"),)),
        chapter_ii_scope(not_for_retail_sale_observed=True),
        chapter_ii_scope(institutional_or_industrial_confirmed=True),
        chapter_ii_scope(),
    ):
        assert decision.rule_id == CHAPTER_SCOPE_RULE_ID
