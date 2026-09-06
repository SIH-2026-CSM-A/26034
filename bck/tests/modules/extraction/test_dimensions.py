"""Tests for Rule 6(1)(f) Dimensions normalisation parser."""

from decimal import Decimal

import pytest

from app.modules.extraction.dimensions import (
    CONFIDENCE_EXPLICIT_DIMENSIONS,
    CONFIDENCE_NOT_APPLICABLE,
    CONFIDENCE_PARSED_DIMENSIONS,
    normalise_dimensions,
)
from app.modules.extraction.types import DimensionsValue, ReasonCode

# Parametrized test cases:
# (input_text, is_applicable_param, exp_success, exp_len, exp_wid,
#  exp_hgt, exp_dia, exp_unit, exp_conf, exp_reason)
DIMENSIONS_TEST_CASES = [
    (
        "10 cm",
        True,
        True,
        Decimal("10"),
        None,
        None,
        None,
        "cm",
        CONFIDENCE_PARSED_DIMENSIONS,
        None,
    ),
    (
        "Length: 15 cm",
        True,
        True,
        Decimal("15"),
        None,
        None,
        None,
        "cm",
        CONFIDENCE_EXPLICIT_DIMENSIONS,
        None,
    ),
    (
        "Width: 10 cm",
        True,
        True,
        None,
        Decimal("10"),
        None,
        None,
        "cm",
        CONFIDENCE_EXPLICIT_DIMENSIONS,
        None,
    ),
    (
        "Height: 10 cm",
        True,
        True,
        None,
        None,
        Decimal("10"),
        None,
        "cm",
        CONFIDENCE_EXPLICIT_DIMENSIONS,
        None,
    ),
    (
        "10 cm x 20 cm",
        True,
        True,
        Decimal("10"),
        Decimal("20"),
        None,
        None,
        "cm",
        CONFIDENCE_PARSED_DIMENSIONS,
        None,
    ),
    (
        "10 x 20 cm",
        True,
        True,
        Decimal("10"),
        Decimal("20"),
        None,
        None,
        "cm",
        CONFIDENCE_PARSED_DIMENSIONS,
        None,
    ),
    (
        "Dimensions: 10 cm x 20 cm x 5 cm",
        True,
        True,
        Decimal("10"),
        Decimal("20"),
        Decimal("5"),
        None,
        "cm",
        CONFIDENCE_EXPLICIT_DIMENSIONS,
        None,
    ),
    (
        "10 x 20 x 5 mm",
        True,
        True,
        Decimal("10"),
        Decimal("20"),
        Decimal("5"),
        None,
        "mm",
        CONFIDENCE_PARSED_DIMENSIONS,
        None,
    ),
    (
        "Diameter: 10 cm",
        True,
        True,
        None,
        None,
        None,
        Decimal("10"),
        "cm",
        CONFIDENCE_EXPLICIT_DIMENSIONS,
        None,
    ),
    (
        "5.5 cm dia",
        True,
        True,
        None,
        None,
        None,
        Decimal("5.5"),
        "cm",
        CONFIDENCE_PARSED_DIMENSIONS,
        None,
    ),
    (
        "Length 12 inch",
        True,
        True,
        Decimal("12"),
        None,
        None,
        None,
        "inch",
        CONFIDENCE_PARSED_DIMENSIONS,
        None,
    ),
    (
        "1.2 m x 0.8 m",
        True,
        True,
        Decimal("1.2"),
        Decimal("0.8"),
        None,
        None,
        "m",
        CONFIDENCE_PARSED_DIMENSIONS,
        None,
    ),
    (
        "N/A",
        True,
        True,
        None,
        None,
        None,
        None,
        None,
        CONFIDENCE_NOT_APPLICABLE,
        ReasonCode.NOT_APPLICABLE,
    ),
    (
        "Not Applicable",
        True,
        True,
        None,
        None,
        None,
        None,
        None,
        CONFIDENCE_NOT_APPLICABLE,
        ReasonCode.NOT_APPLICABLE,
    ),
    (
        "Sizes: 1.5 m x 2.0 m",
        True,
        True,
        Decimal("1.5"),
        Decimal("2.0"),
        None,
        None,
        "m",
        CONFIDENCE_EXPLICIT_DIMENSIONS,
        None,
    ),
    (
        "",
        False,
        True,
        None,
        None,
        None,
        None,
        None,
        CONFIDENCE_NOT_APPLICABLE,
        ReasonCode.NOT_APPLICABLE,
    ),
    (
        "",
        True,
        False,
        None,
        None,
        None,
        None,
        None,
        0.0,
        ReasonCode.EMPTY_INPUT,
    ),
    (
        "10 x abc cm",
        True,
        False,
        None,
        None,
        None,
        None,
        None,
        0.0,
        ReasonCode.UNPARSEABLE_FORMAT,
    ),
    (
        "10 cm x",
        True,
        False,
        None,
        None,
        None,
        None,
        None,
        0.0,
        ReasonCode.UNPARSEABLE_FORMAT,
    ),
    (
        "10 x 20 foos",
        True,
        False,
        None,
        None,
        None,
        None,
        None,
        0.0,
        ReasonCode.UNRECOGNIZED_UNIT,
    ),
]


@pytest.mark.parametrize(
    (
        "input_text",
        "is_applicable_param",
        "exp_success",
        "exp_len",
        "exp_wid",
        "exp_hgt",
        "exp_dia",
        "exp_unit",
        "exp_conf",
        "exp_reason",
    ),
    DIMENSIONS_TEST_CASES,
)
def test_normalise_dimensions_cases(
    input_text,
    is_applicable_param,
    exp_success,
    exp_len,
    exp_wid,
    exp_hgt,
    exp_dia,
    exp_unit,
    exp_conf,
    exp_reason,
):
    res = normalise_dimensions(input_text, is_applicable=is_applicable_param)
    assert res.success is exp_success
    assert res.reason_code == exp_reason
    if exp_success:
        assert res.confidence == exp_conf
        assert res.value is not None
        assert isinstance(res.value, DimensionsValue)
        assert res.value.length == exp_len
        assert res.value.width == exp_wid
        assert res.value.height == exp_hgt
        assert res.value.diameter == exp_dia
        assert res.value.unit == exp_unit
    else:
        assert res.confidence == 0.0
        assert res.value is None


def test_not_applicable_is_not_unparseable():
    """Verify non-applicable dimensions return NOT_APPLICABLE, not UNPARSEABLE_FORMAT."""
    res = normalise_dimensions("N/A", is_applicable=True)
    assert res.success is True
    assert res.reason_code == ReasonCode.NOT_APPLICABLE
    assert res.reason_code != ReasonCode.UNRECOGNIZED_UNIT
    assert res.reason_code != ReasonCode.UNPARSEABLE_FORMAT
    assert res.value is not None
    assert res.value.is_applicable is False

    res_param = normalise_dimensions("Any String", is_applicable=False)
    assert res_param.success is True
    assert res_param.reason_code == ReasonCode.NOT_APPLICABLE
    assert res_param.reason_code != ReasonCode.UNPARSEABLE_FORMAT
    assert res_param.value is not None
    assert res_param.value.is_applicable is False
