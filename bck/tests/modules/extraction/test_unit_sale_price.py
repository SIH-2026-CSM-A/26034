"""Tests for Rule 6(11) Unit Sale Price normalisation parser."""

from decimal import Decimal

import pytest

from app.modules.extraction.types import (
    NetQuantityValue,
    ReasonCode,
    UnitSalePriceValue,
)
from app.modules.extraction.unit_sale_price import (
    CONFIDENCE_EXPLICIT_UNIT_SALE_PRICE,
    CONFIDENCE_PARSED_UNIT_SALE_PRICE,
    normalise_unit_sale_price,
)

# Parametrized test cases:
# (input_text, net_q, exp_success, exp_price, exp_basis, exp_conf, exp_reason)
USP_TEST_CASES = [
    # Mass < 1 kg -> g basis
    (
        "Rs. 0.50 / g",
        NetQuantityValue(value=Decimal("500"), unit="g"),
        True,
        Decimal("0.50"),
        "g",
        CONFIDENCE_PARSED_UNIT_SALE_PRICE,
        None,
    ),
    # Mass < 1 kg -> kg basis (WRONG BASIS)
    (
        "Rs. 500 / kg",
        NetQuantityValue(value=Decimal("500"), unit="g"),
        False,
        None,
        None,
        0.0,
        ReasonCode.INVALID_VALUE,
    ),
    # Mass == 1 kg -> kg basis
    (
        "Unit Sale Price: ₹ 200 / kg",
        NetQuantityValue(value=Decimal("1000"), unit="g"),
        True,
        Decimal("200"),
        "kg",
        CONFIDENCE_EXPLICIT_UNIT_SALE_PRICE,
        None,
    ),
    # Mass > 1 kg -> kg basis
    (
        "USP: Rs 150 / kg",
        NetQuantityValue(value=Decimal("2"), unit="kg"),
        True,
        Decimal("150"),
        "kg",
        CONFIDENCE_EXPLICIT_UNIT_SALE_PRICE,
        None,
    ),
    # Mass > 1 kg -> g basis (WRONG BASIS)
    (
        "USP: Rs 0.15 / g",
        NetQuantityValue(value=Decimal("2"), unit="kg"),
        False,
        None,
        None,
        0.0,
        ReasonCode.INVALID_VALUE,
    ),
    # Volume < 1 L -> ml basis
    (
        "₹ 0.25 / ml",
        NetQuantityValue(value=Decimal("250"), unit="ml"),
        True,
        Decimal("0.25"),
        "ml",
        CONFIDENCE_PARSED_UNIT_SALE_PRICE,
        None,
    ),
    # Volume < 1 L -> litre basis (WRONG BASIS)
    (
        "Rs 250 / litre",
        NetQuantityValue(value=Decimal("250"), unit="ml"),
        False,
        None,
        None,
        0.0,
        ReasonCode.INVALID_VALUE,
    ),
    # Volume == 1 L -> litre basis
    (
        "Unit Price: Rs 80 / litre",
        NetQuantityValue(value=Decimal("1"), unit="l"),
        True,
        Decimal("80"),
        "litre",
        CONFIDENCE_EXPLICIT_UNIT_SALE_PRICE,
        None,
    ),
    # Volume > 1 L -> litre basis
    (
        "Rs 90 / l",
        NetQuantityValue(value=Decimal("2"), unit="l"),
        True,
        Decimal("90"),
        "litre",
        CONFIDENCE_PARSED_UNIT_SALE_PRICE,
        None,
    ),
    # Volume > 1 L -> ml basis (WRONG BASIS)
    (
        "Rs 0.09 / ml",
        NetQuantityValue(value=Decimal("2"), unit="l"),
        False,
        None,
        None,
        0.0,
        ReasonCode.INVALID_VALUE,
    ),
    # Length < 1 m -> cm basis
    (
        "Rs 2.00 per cm",
        NetQuantityValue(value=Decimal("50"), unit="cm"),
        True,
        Decimal("2.00"),
        "cm",
        CONFIDENCE_PARSED_UNIT_SALE_PRICE,
        None,
    ),
    # Length < 1 m -> m basis (WRONG BASIS)
    (
        "Rs 200 per m",
        NetQuantityValue(value=Decimal("50"), unit="cm"),
        False,
        None,
        None,
        0.0,
        ReasonCode.INVALID_VALUE,
    ),
    # Length == 1 m -> metre basis
    (
        "Unit Sale Price: ₹ 200 per metre",
        NetQuantityValue(value=Decimal("1"), unit="m"),
        True,
        Decimal("200"),
        "metre",
        CONFIDENCE_EXPLICIT_UNIT_SALE_PRICE,
        None,
    ),
    # Length > 1 m -> metre basis
    (
        "Rs 150 / m",
        NetQuantityValue(value=Decimal("5"), unit="m"),
        True,
        Decimal("150"),
        "metre",
        CONFIDENCE_PARSED_UNIT_SALE_PRICE,
        None,
    ),
    # Length > 1 m -> cm basis (WRONG BASIS)
    (
        "Rs 1.50 / cm",
        NetQuantityValue(value=Decimal("5"), unit="m"),
        False,
        None,
        None,
        0.0,
        ReasonCode.INVALID_VALUE,
    ),
    # Count basis
    (
        "Rs 10 / piece",
        NetQuantityValue(value=Decimal("5"), unit="N"),
        True,
        Decimal("10"),
        "N",
        CONFIDENCE_PARSED_UNIT_SALE_PRICE,
        None,
    ),
    # Unsupported net quantity unit -> INVALID_VALUE
    (
        "Rs 50 / g",
        NetQuantityValue(value=Decimal("500"), unit="unsupported_boxes"),
        False,
        None,
        None,
        0.0,
        ReasonCode.INVALID_VALUE,
    ),
    # Standalone without net_quantity
    (
        "USP: Rs 50 / g",
        None,
        True,
        Decimal("50"),
        "g",
        CONFIDENCE_EXPLICIT_UNIT_SALE_PRICE,
        None,
    ),
    # Unrecognized basis unit
    (
        "Rs 10 per widget",
        None,
        False,
        None,
        None,
        0.0,
        ReasonCode.UNRECOGNIZED_UNIT,
    ),
    # Unparseable format
    (
        "Unit price is very cheap",
        None,
        False,
        None,
        None,
        0.0,
        ReasonCode.UNPARSEABLE_FORMAT,
    ),
    # Empty string
    (
        "",
        None,
        False,
        None,
        None,
        0.0,
        ReasonCode.EMPTY_INPUT,
    ),
]


@pytest.mark.parametrize(
    (
        "input_text",
        "net_q",
        "exp_success",
        "exp_price",
        "exp_basis",
        "exp_conf",
        "exp_reason",
    ),
    USP_TEST_CASES,
)
def test_normalise_unit_sale_price_cases(
    input_text,
    net_q,
    exp_success,
    exp_price,
    exp_basis,
    exp_conf,
    exp_reason,
):
    res = normalise_unit_sale_price(input_text, net_quantity=net_q)
    assert res.success is exp_success
    assert res.reason_code == exp_reason
    if exp_success:
        assert res.confidence == exp_conf
        assert res.value is not None
        assert isinstance(res.value, UnitSalePriceValue)
        assert res.value.unit_price == exp_price
        assert res.value.unit_basis == exp_basis
    else:
        assert res.confidence == 0.0
        assert res.value is None
