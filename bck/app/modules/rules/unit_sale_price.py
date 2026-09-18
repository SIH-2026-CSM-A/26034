"""Rule 6(11) — the unit basis a unit sale price must be declared on.

A format rule. The gazette says a price per gram below a kilogram and per kilogram at or
above it, and the same shape for length, volume and count; it says nothing about how
close the figure must be to the retail price divided by the quantity. So nothing here
divides anything: the only question asked is whether the basis printed after "per" is the
one the net quantity calls for.

The thresholds and the bases are read from the store. The factors that put a net quantity
in the threshold's unit are physical facts — a gram is a thousandth of a kilogram — and
the one kind of figure this module may hold.
"""

from decimal import Decimal

from .base import Verdict
from .conditions import UnitSalePriceBasisCondition
from .evaluator import evaluate_rule
from .loader import rule_by_id
from .results import StrictRuleModel

UNIT_SALE_PRICE_RULE_ID = "R6-11-UNIT-SALE-PRICE"

TO_THRESHOLD_UNIT: dict[tuple[str, str], Decimal] = {
    ("g", "kg"): Decimal("0.001"),
    ("kg", "kg"): Decimal(1),
    ("cm", "m"): Decimal("0.01"),
    ("m", "m"): Decimal(1),
    ("ml", "l"): Decimal("0.001"),
    ("l", "l"): Decimal(1),
}
"""``(quantity unit, threshold unit)`` to the factor between them."""


class UnitSalePriceEvaluation(StrictRuleModel):
    """What Rule 6(11) requires for this net quantity, and whether the label matches."""

    verdict: Verdict
    required_basis: str
    declared_basis: str


def _condition() -> UnitSalePriceBasisCondition:
    condition = rule_by_id(UNIT_SALE_PRICE_RULE_ID).conditions
    if not isinstance(condition, UnitSalePriceBasisCondition):
        raise TypeError(f"{UNIT_SALE_PRICE_RULE_ID} does not contain a unit-sale-price condition")
    return condition


def known_unit_sale_price_bases() -> frozenset[str]:
    """Every basis the store can require. A printed basis outside this set cannot be judged."""
    condition = _condition()
    return frozenset(
        {condition.count_basis}
        | {limb.below_threshold_basis for limb in condition.bases}
        | {limb.at_or_above_threshold_basis for limb in condition.bases}
    )


def required_unit_sale_price_basis(quantity: Decimal, unit: str) -> str | None:
    """The basis Rule 6(11) prescribes for a net quantity, or ``None`` if it speaks to none.

    ``None`` is for a unit the rule has no limb for. It is not "any basis will do": a
    caller that receives it has a quantity the rule does not address and should say so.
    """
    condition = _condition()
    if unit in condition.count_units:
        return condition.count_basis
    for limb in condition.bases:
        if unit not in limb.quantity_units:
            continue
        in_threshold_units = quantity * TO_THRESHOLD_UNIT[unit, limb.threshold_unit]
        if in_threshold_units < limb.threshold:
            return limb.below_threshold_basis
        return limb.at_or_above_threshold_basis
    return None


def evaluate_unit_sale_price_basis(
    declared_basis: str, quantity: Decimal, unit: str
) -> UnitSalePriceEvaluation | None:
    """Compare the basis printed on the package with the one its net quantity calls for.

    ``None`` where the rule has no limb for the quantity's unit. Otherwise a match is a
    PASS and anything else proposes the rule's own severity — subject, as everywhere, to
    :func:`~app.modules.rules.evaluator.evaluate_rule`'s source-status gate.
    """
    required = required_unit_sale_price_basis(quantity, unit)
    if required is None:
        return None
    proposed = Verdict.PASS if declared_basis == required else Verdict.POTENTIAL_VIOLATION
    return UnitSalePriceEvaluation(
        verdict=evaluate_rule(rule_by_id(UNIT_SALE_PRICE_RULE_ID), proposed),
        required_basis=required,
        declared_basis=declared_basis,
    )
