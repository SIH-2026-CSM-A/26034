"""Rule 6(11): the basis a unit sale price must be declared on, read from the store."""

from decimal import Decimal

import pytest

from app.modules.rules import (
    Verdict,
    evaluate_unit_sale_price_basis,
    known_unit_sale_price_bases,
    required_unit_sale_price_basis,
)


@pytest.mark.parametrize(
    ("quantity", "unit", "basis"),
    [
        (Decimal(500), "g", "g"),
        (Decimal("999.99"), "g", "g"),
        (Decimal(1000), "g", "kg"),
        (Decimal("0.5"), "kg", "g"),
        (Decimal(1), "kg", "kg"),
        (Decimal(250), "ml", "ml"),
        (Decimal(1), "l", "litre"),
        (Decimal("2.5"), "l", "litre"),
        (Decimal(50), "cm", "cm"),
        (Decimal(100), "cm", "metre"),
        (Decimal(3), "m", "metre"),
        (Decimal(10), "N", "N"),
        (Decimal(6), "pcs", "N"),
    ],
)
def test_the_basis_follows_the_gazette_threshold(quantity, unit, basis) -> None:
    assert required_unit_sale_price_basis(quantity, unit) == basis


def test_a_unit_the_rule_has_no_limb_for_requires_nothing() -> None:
    assert required_unit_sale_price_basis(Decimal(5), "mm") is None
    assert evaluate_unit_sale_price_basis("g", Decimal(5), "mm") is None


def test_the_evaluation_compares_the_basis_and_only_the_basis() -> None:
    assert evaluate_unit_sale_price_basis("g", Decimal(500), "g").verdict is Verdict.PASS
    wrong = evaluate_unit_sale_price_basis("kg", Decimal(500), "g")
    assert wrong.verdict is Verdict.POTENTIAL_VIOLATION
    assert (wrong.required_basis, wrong.declared_basis) == ("g", "kg")


def test_every_basis_the_store_can_require_is_known() -> None:
    assert known_unit_sale_price_bases() == {"g", "kg", "ml", "litre", "cm", "metre", "N"}
