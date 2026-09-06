"""Tests for Rule 6(1)(b) Commodity Name normalisation parser."""

import pytest

from app.modules.extraction.commodity_name import (
    CONFIDENCE_EXPLICIT_NAME_DECLARATION,
    CONFIDENCE_MULTI_PRODUCT_COMBINATION,
    CONFIDENCE_PARSED_COMMODITY_NAME,
    normalise_commodity_name,
)
from app.modules.extraction.types import (
    CommodityNameValue,
    ReasonCode,
)

# Parametrized test cases:
# (input_text, exp_success, exp_primary, exp_item_count, exp_is_multi,
#  exp_items, exp_conf, exp_reason)
COMMODITY_NAME_TEST_CASES = [
    (
        "Toothpaste",
        True,
        "Toothpaste",
        1,
        False,
        [("Toothpaste", None)],
        CONFIDENCE_PARSED_COMMODITY_NAME,
        None,
    ),
    (
        "Generic Name: Toothpaste",
        True,
        "Toothpaste",
        1,
        False,
        [("Toothpaste", None)],
        CONFIDENCE_EXPLICIT_NAME_DECLARATION,
        None,
    ),
    (
        "Commodity Name: Wheat Flour",
        True,
        "Wheat Flour",
        1,
        False,
        [("Wheat Flour", None)],
        CONFIDENCE_EXPLICIT_NAME_DECLARATION,
        None,
    ),
    (
        "Product Name: Bath Soap",
        True,
        "Bath Soap",
        1,
        False,
        [("Bath Soap", None)],
        CONFIDENCE_EXPLICIT_NAME_DECLARATION,
        None,
    ),
    (
        "Toothpaste 100g, Toothbrush 1 N",
        True,
        "Toothpaste, Toothbrush",
        2,
        True,
        [("Toothpaste", "100g"), ("Toothbrush", "1 N")],
        CONFIDENCE_MULTI_PRODUCT_COMBINATION,
        None,
    ),
    (
        "Toothpaste (100 g) + Toothbrush (1 piece)",
        True,
        "Toothpaste, Toothbrush",
        2,
        True,
        [("Toothpaste", "100 g"), ("Toothbrush", "1 piece")],
        CONFIDENCE_MULTI_PRODUCT_COMBINATION,
        None,
    ),
    (
        "Package Contains: Toothpaste 100g, Toothbrush 1 N",
        True,
        "Toothpaste, Toothbrush",
        2,
        True,
        [("Toothpaste", "100g"), ("Toothbrush", "1 N")],
        CONFIDENCE_MULTI_PRODUCT_COMBINATION,
        None,
    ),
    (
        "Shampoo 200ml; Conditioner 100ml",
        True,
        "Shampoo, Conditioner",
        2,
        True,
        [("Shampoo", "200ml"), ("Conditioner", "100ml")],
        CONFIDENCE_MULTI_PRODUCT_COMBINATION,
        None,
    ),
    (
        "1 N Razor and 2 N Cartridges",
        True,
        "Razor, Cartridges",
        2,
        True,
        [("Razor", "1 N"), ("Cartridges", "2 N")],
        CONFIDENCE_MULTI_PRODUCT_COMBINATION,
        None,
    ),
    (
        "Combination Package: Soap 100g, Face Wash 50ml",
        True,
        "Soap, Face Wash",
        2,
        True,
        [("Soap", "100g"), ("Face Wash", "50ml")],
        CONFIDENCE_MULTI_PRODUCT_COMBINATION,
        None,
    ),
    (
        "Contains: 1 N Soap (100g), 1 N Shampoo (200ml), 1 N Comb",
        True,
        "Soap, Shampoo, Comb",
        3,
        True,
        [("Soap", "1 N, 100g"), ("Shampoo", "1 N, 200ml"), ("Comb", "1 N")],
        CONFIDENCE_MULTI_PRODUCT_COMBINATION,
        None,
    ),
    (
        "Biscuits 100g",
        True,
        "Biscuits",
        1,
        False,
        [("Biscuits", "100g")],
        CONFIDENCE_PARSED_COMMODITY_NAME,
        None,
    ),
    (
        "Name of Commodity: Milk Powder",
        True,
        "Milk Powder",
        1,
        False,
        [("Milk Powder", None)],
        CONFIDENCE_EXPLICIT_NAME_DECLARATION,
        None,
    ),
    (
        "Multi-pack: 2 N Shaving Cream (50g) + 1 N Brush",
        True,
        "Shaving Cream, Brush",
        2,
        True,
        [("Shaving Cream", "2 N, 50g"), ("Brush", "1 N")],
        CONFIDENCE_MULTI_PRODUCT_COMBINATION,
        None,
    ),
    (
        "Soap + Shampoo",
        False,
        None,
        0,
        False,
        None,
        0.0,
        ReasonCode.UNPARSEABLE_FORMAT,
    ),
    (
        "1 N Soap + Shampoo",
        False,
        None,
        0,
        False,
        None,
        0.0,
        ReasonCode.UNPARSEABLE_FORMAT,
    ),
    ("", False, None, 0, False, None, 0.0, ReasonCode.EMPTY_INPUT),
    ("   ", False, None, 0, False, None, 0.0, ReasonCode.EMPTY_INPUT),
    (
        "Manufactured by XYZ Pvt Ltd Industrial Area Phase 1",
        False,
        None,
        0,
        False,
        None,
        0.0,
        ReasonCode.UNPARSEABLE_FORMAT,
    ),
    (
        "MRP Rs 100 incl of all taxes",
        False,
        None,
        0,
        False,
        None,
        0.0,
        ReasonCode.UNPARSEABLE_FORMAT,
    ),
]


@pytest.mark.parametrize(
    (
        "input_text",
        "exp_success",
        "exp_primary",
        "exp_item_count",
        "exp_is_multi",
        "exp_items",
        "exp_conf",
        "exp_reason",
    ),
    COMMODITY_NAME_TEST_CASES,
)
def test_normalise_commodity_name_cases(
    input_text,
    exp_success,
    exp_primary,
    exp_item_count,
    exp_is_multi,
    exp_items,
    exp_conf,
    exp_reason,
):
    res = normalise_commodity_name(input_text)
    assert res.success is exp_success
    assert res.reason_code == exp_reason
    if exp_success:
        assert res.confidence == exp_conf
        assert res.value is not None
        assert isinstance(res.value, CommodityNameValue)
        assert res.value.primary_name == exp_primary
        assert len(res.value.items) == exp_item_count
        assert res.value.is_multi_product is exp_is_multi
        if exp_items:
            for idx, (exp_name, exp_qty) in enumerate(exp_items):
                assert res.value.items[idx].name == exp_name
                assert res.value.items[idx].quantity_or_count == exp_qty
    else:
        assert res.confidence == 0.0
        assert res.value is None


def test_multi_product_preserves_every_item():
    """Verify that multi-product normalisation preserves every item and quantity."""
    input_text = "Contains: 1 N Toothpaste (100g) + 2 N Toothbrush"
    res = normalise_commodity_name(input_text)
    assert res.success is True
    assert res.value is not None
    assert res.value.is_multi_product is True
    assert len(res.value.items) == 2

    item1 = res.value.items[0]
    assert item1.name == "Toothpaste"
    assert item1.quantity_or_count == "1 N, 100g"

    item2 = res.value.items[1]
    assert item2.name == "Toothbrush"
    assert item2.quantity_or_count == "2 N"
