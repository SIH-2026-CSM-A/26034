"""Tests for deterministic Rule 7 calculations and routing."""

from datetime import date
from decimal import Decimal

import pytest

from app.modules.rules import (
    ProductCategory,
    Rule7Route,
    Verdict,
    WidthRatioResult,
    calculate_cylindrical_pdp_area,
    calculate_other_shape_pdp_area,
    calculate_rectangular_pdp_area,
    evaluate_rule7_height,
    evaluate_rule7_width,
    minimum_character_height,
    rule7_requirements_apply,
    validate_width_to_height,
)

EVALUATION_DATE = date(2026, 9, 6)


@pytest.mark.parametrize(
    ("area", "normal_height", "moulded_height"),
    [
        ("50.0", "1.0", "1.5"),
        ("50.0001", "1.5", "3.0"),
        ("100.0", "1.5", "3.0"),
        ("100.0001", "2.5", "4.0"),
        ("500.0", "2.5", "4.0"),
        ("500.0001", "4.0", "6.0"),
        ("2500.0", "4.0", "6.0"),
        ("2500.0001", "6.0", "6.0"),
    ],
)
def test_table_i_boundaries_for_both_columns(
    area: str,
    normal_height: str,
    moulded_height: str,
) -> None:
    """Each inclusive upper boundary must remain in its lower Table-I band."""
    panel_area = Decimal(area)

    assert minimum_character_height(
        panel_area,
        is_blown_formed_or_moulded=False,
        product_category=None,
        evaluation_date=EVALUATION_DATE,
    ) == Decimal(normal_height)
    assert minimum_character_height(
        panel_area,
        is_blown_formed_or_moulded=True,
        product_category=None,
        evaluation_date=EVALUATION_DATE,
    ) == Decimal(moulded_height)


@pytest.mark.parametrize(
    ("width", "height", "expected"),
    [
        ("2", "6", WidthRatioResult.MEETS),
        ("1.999", "6", WidthRatioResult.DOES_NOT_MEET),
    ],
)
def test_rule_7_3_normal_ratio_behavior(
    width: str,
    height: str,
    expected: WidthRatioResult,
) -> None:
    """Ordinary characters must meet the one-third width threshold exactly."""
    assert validate_width_to_height("A", Decimal(width), Decimal(height)) is expected


@pytest.mark.parametrize("character", ["1", "i", "I", "l"])
def test_rule_7_3_legal_exceptions(character: str) -> None:
    """Every named Rule 7(3) exception must bypass the ratio requirement."""
    assert (
        validate_width_to_height(character, Decimal("0.1"), Decimal("6")) is WidthRatioResult.EXEMPT
    )


def test_rule_7_4_rectangular_formula() -> None:
    """A rectangular PDP must use the supplied display-side height and width."""
    assert calculate_rectangular_pdp_area(Decimal("12"), Decimal("5")) == Decimal("60")


@pytest.mark.parametrize("nearly_cylindrical", [False, True])
def test_rule_7_4_cylindrical_formula(nearly_cylindrical: bool) -> None:
    """Cylindrical and nearly cylindrical packages must use the same 40% formula."""
    assert calculate_cylindrical_pdp_area(
        Decimal("10"),
        Decimal("20"),
        nearly_cylindrical=nearly_cylindrical,
    ) == Decimal("80.0")


def test_rule_7_4_other_shape_uses_excluded_surface_area() -> None:
    """Excluded top, bottom, flange, shoulder, and neck area must not enter the 40% basis."""
    assert calculate_other_shape_pdp_area(
        total_surface_area=Decimal("300"),
        excluded_surface_area=Decimal("50"),
    ) == Decimal("100.0")


def test_rule_7_4_other_shape_accepts_legally_identified_pdp_area() -> None:
    """An identified legal PDP area must remain an alternative to the 40% calculation."""
    assert calculate_other_shape_pdp_area(legally_applicable_pdp_area=Decimal("73.5")) == Decimal(
        "73.5"
    )


@pytest.mark.parametrize(
    ("declaration", "expected"),
    [
        ("net_weight", True),
        ("retail_sale_price", True),
        ("expiry_best_before_use_by", True),
        ("consumer_care_details", True),
        ("manufacturer_address", False),
    ],
)
def test_rule_7_5_other_law_carve_out(declaration: str, expected: bool) -> None:
    """Only the four preserved declaration groups retain Rule 7 sizing under another law."""
    assert rule7_requirements_apply(declaration, required_under_other_law=True) is expected


def test_rule_7_5_applies_normally_without_other_law() -> None:
    """The carve-out must not affect declarations governed only by these rules."""
    assert rule7_requirements_apply(
        "manufacturer_address",
        required_under_other_law=False,
    )


def test_medical_device_height_routes_to_review_without_table_lookup() -> None:
    """Medical devices without MDR evidence must REVIEW before ordinary Table-I validation."""
    result = evaluate_rule7_height(
        panel_area=Decimal("-1"),
        measured_height=Decimal("-1"),
        is_blown_formed_or_moulded=False,
        product_category=ProductCategory.MEDICAL_DEVICE,
        evaluation_date=date(2025, 10, 24),
    )

    assert result.route is Rule7Route.SECTOR_FRAMEWORK
    assert result.verdict is Verdict.REVIEW


def test_ordinary_package_height_uses_table_i() -> None:
    """Non-medical packages must evaluate measured height against Table-I."""
    result = evaluate_rule7_height(
        panel_area=Decimal("50"),
        measured_height=Decimal("0.9"),
        is_blown_formed_or_moulded=False,
        product_category=None,
        evaluation_date=date(2025, 10, 24),
    )

    assert result.route is Rule7Route.LMPC_TABLE_I
    assert result.verdict is Verdict.POTENTIAL_VIOLATION


def test_medical_device_width_routes_to_review_without_ratio_validation() -> None:
    """Medical devices without MDR evidence must REVIEW before Rule 7(3) validation."""
    result = evaluate_rule7_width(
        character="A",
        width=Decimal("-1"),
        height=Decimal("-1"),
        product_category=ProductCategory.MEDICAL_DEVICE,
        evaluation_date=date(2025, 10, 24),
    )

    assert result.route is Rule7Route.SECTOR_FRAMEWORK
    assert result.verdict is Verdict.REVIEW
    assert result.ratio_result is None


def test_medical_override_does_not_apply_before_gazette_publication() -> None:
    """A medical package before publication must remain on the then-active LMPC route."""
    result = evaluate_rule7_height(
        panel_area=Decimal("50"),
        measured_height=Decimal("1"),
        is_blown_formed_or_moulded=False,
        product_category=ProductCategory.MEDICAL_DEVICE,
        evaluation_date=date(2025, 10, 23),
    )

    assert result.route is Rule7Route.LMPC_TABLE_I
    assert result.verdict is Verdict.PASS
