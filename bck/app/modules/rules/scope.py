"""Rule 3 — whether Chapter II reaches a package at all.

The question that comes before every other question this module answers. Chapter II is
headed "PROVISIONS APPLICABLE TO PACKAGES INTENDED FOR RETAIL SALE" and Rule 3 names the
packages it does not reach. Every obligation in the store today — Rule 6 declarations,
Rule 7 dimensions, Rule 8 placement, Rule 9 manner — sits inside that chapter, so a
package Rule 3 excludes owes none of them.

**An excluded package is NOT_APPLICABLE, never FAIL.** The duty does not exist for it.
That is a different thing from Rule 26, which exempts a package still inside the chapter,
and a different thing again from a sector override, which moves one obligation to another
framework while the rest stay here.

**Retail is the default and exclusion is the exception.** The chapter heading says so, and
Rule 3 is written as a list of things it does not apply to. So an unreadable net quantity
establishes no exclusion and leaves the package governed — the burden sits on establishing
the exception, not on disproving it. The alternative, suspending Chapter II whenever a
quantity is illegible, would turn every poor photograph into a verdict that says nothing.

**Nothing here infers an exclusion from an absence.** A package with no ``not for retail
sale`` mark is not thereby a retail package; it is a package about which Rule 3(c) has said
nothing, and it evaluates exactly as it would have done had this module not existed.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from decimal import Decimal

from app.contracts import NormalisedField

from .base import ScopeStatus
from .conditions import ChapterScopeCondition
from .loader import rule_by_id
from .results import ScopeDecision

CHAPTER_SCOPE_RULE_ID = "R3-CHAPTER-II-SCOPE"

WEIGHT_UNITS_TO_KG: dict[str, Decimal] = {"kg": Decimal(1), "g": Decimal("0.001")}
"""Canonical weight units and their factor to kilogram.

``N`` and ``pcs`` are absent deliberately, and neither is a force. ``app.modules.extraction``
canonicalises "number", "no" and "num" to ``N``, so both are *counts* — Rule 3(a) states its
threshold in "kilogram or litre", and a count of anything can never satisfy it.
"""

VOLUME_UNITS_TO_L: dict[str, Decimal] = {"l": Decimal(1), "ml": Decimal("0.001")}
"""Canonical volume units and their factor to litre."""


def _condition() -> ChapterScopeCondition:
    """The Rule 3 parameters, read from the store rather than written here.

    Every figure this module compares against is in ``data/rules.yaml`` and is cited to the
    compilation. A threshold inlined in Python is a threshold no gazette backs, and nothing
    downstream could tell the two apart.
    """
    condition = rule_by_id(CHAPTER_SCOPE_RULE_ID).conditions
    if not isinstance(condition, ChapterScopeCondition):
        raise TypeError(f"{CHAPTER_SCOPE_RULE_ID} does not contain a chapter-scope condition")
    return condition


def _normalise(text: str) -> str:
    """Collapse whitespace and case so a printed marker matches its stored phrase."""
    return " ".join(text.split()).casefold()


def not_for_retail_sale_declared(texts: Iterable[str]) -> bool:
    """Whether any of ``texts`` bears the marker Rule 2(bb) and 2(bc) require.

    The phrase comes from the store, not from this file. Matching is case-insensitive and
    whitespace-collapsed because a package prints it in whatever case the artwork used and
    OCR reports the spacing it saw.

    A ``True`` here never decides anything on its own — it routes to an officer. That
    asymmetry is what makes a substring match acceptable evidence: a false positive costs a
    review, and a false negative leaves the package evaluated exactly as it is today.
    """
    marker = _normalise(_condition().not_for_retail_sale_marker)
    return any(marker in _normalise(text) for text in texts)


def _exceeds_rule_3a(field: NormalisedField, condition: ChapterScopeCondition) -> bool | None:
    """Whether one declared quantity is beyond Rule 3(a), or ``None`` if not comparable.

    ``None`` covers both a quantity we could not canonicalise and one measured in a unit
    Rule 3(a) does not speak — a count. Neither establishes anything, and neither is the
    same as a quantity that is within the threshold.
    """
    if field.numeric_value is None or field.unit is None:
        return None
    if field.unit in WEIGHT_UNITS_TO_KG:
        kilograms = field.numeric_value * WEIGHT_UNITS_TO_KG[field.unit]
        return kilograms > condition.maximum_weight_inclusive_kg
    if field.unit in VOLUME_UNITS_TO_L:
        litres = field.numeric_value * VOLUME_UNITS_TO_L[field.unit]
        return litres > condition.maximum_volume_inclusive_l
    return None


def rule_3b_is_subsumed_by_rule_3a() -> bool:
    """Whether Rule 3(b) can ever exclude a package Rule 3(a) has not already excluded.

    ``False`` would mean Rule 3(b) has become operative and needs an input of its own —
    a confirmed commodity class, which no photograph establishes.

    On the corpus text as it stands this is ``True``, and that is why no Rule 3(b) branch
    exists in :func:`chapter_ii_scope`. Rule 3(a) excludes a quantity of more than 25
    kilogram; Rule 3(b) excludes cement, fertilizer and agricultural farm produce in bags
    above 50 kilogram. Every package the second names weighs more than the first's
    threshold, so confirming Rule 3(b) could not change an answer Rule 3(a) has not already
    given. An officer-confirmation path for it would be a branch that can never fire.

    Read from the store rather than asserted, so an amendment to either figure answers this
    question again instead of leaving a stale comment behind.
    """
    condition = _condition()
    return condition.bagged_maximum_inclusive_kg >= condition.maximum_weight_inclusive_kg


def chapter_ii_scope(
    *,
    net_quantity: Sequence[NormalisedField] = (),
    not_for_retail_sale_observed: bool = False,
    institutional_or_industrial_confirmed: bool = False,
) -> ScopeDecision:
    """Whether Chapter II governs this package, and under which limb of Rule 3.

    Answered once per scan. The limbs are tested in order of what they establish rather
    than in the order the gazette prints them: a confirmed exclusion outranks an inferred
    one, an inferred one outranks an indicated one, and anything unestablished leaves the
    package governed.

    Rule 3(b) has no branch. See :func:`rule_3b_is_subsumed_by_rule_3a`.
    """
    condition = _condition()

    if institutional_or_industrial_confirmed:
        return ScopeDecision(
            status=ScopeStatus.EXCLUDED,
            reason=(
                "an officer has confirmed this package is supplied to an industrial or "
                "institutional consumer. Rule 3(c) disapplies Chapter II to such packages, "
                "so this obligation does not arise under these Rules."
            ),
            rule_id=CHAPTER_SCOPE_RULE_ID,
            limb="Rule 3(c)",
        )

    comparisons = [
        exceeded
        for exceeded in (_exceeds_rule_3a(field, condition) for field in net_quantity)
        if exceeded is not None
    ]

    if comparisons and all(comparisons):
        return ScopeDecision(
            status=ScopeStatus.EXCLUDED,
            reason=(
                f"Rule 3(a) disapplies Chapter II to a package containing a quantity of more "
                f"than {condition.maximum_weight_inclusive_kg} kilogram or "
                f"{condition.maximum_volume_inclusive_l} litre. The declared net quantity is "
                f"beyond that, so this obligation does not arise under these Rules."
            ),
            rule_id=CHAPTER_SCOPE_RULE_ID,
            limb="Rule 3(a)",
        )

    if any(comparisons):
        return ScopeDecision(
            status=ScopeStatus.UNCERTAIN,
            reason=(
                f"this package declares more than one net quantity, and they fall on opposite "
                f"sides of the Rule 3(a) threshold of "
                f"{condition.maximum_weight_inclusive_kg} kilogram or "
                f"{condition.maximum_volume_inclusive_l} litre. Which quantity Rule 3(a) is to "
                f"be read against is not settled by the label."
            ),
            rule_id=CHAPTER_SCOPE_RULE_ID,
            limb="Rule 3(a)",
        )

    if not_for_retail_sale_observed:
        return ScopeDecision(
            status=ScopeStatus.UNCERTAIN,
            reason=(
                f"this package bears the declaration "
                f"'{condition.not_for_retail_sale_marker}', which Rule 2(bb) and Rule 2(bc) "
                f"require of a package supplied to an industrial or institutional consumer, "
                f"and Rule 3(c) disapplies Chapter II to such packages. Whether this package "
                f"was in fact so supplied is not established by the label. Confirm it to "
                f"settle the obligation either way."
            ),
            rule_id=CHAPTER_SCOPE_RULE_ID,
            limb="Rule 3(c)",
        )

    return ScopeDecision(
        status=ScopeStatus.GOVERNED,
        reason="Chapter II applies to this package; no limb of Rule 3 excludes it.",
        rule_id=CHAPTER_SCOPE_RULE_ID,
    )
