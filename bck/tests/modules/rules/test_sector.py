"""Tests for sector overrides — carve-outs routed by confirmed product category.

The load-bearing claim under test is that a sector override *removes* an obligation from
the packaged rules rather than tightening it, and that the routing is table lookup over
the rule store rather than a branch anyone has to remember to extend.
"""

from datetime import date
from decimal import Decimal

import pytest

from app.modules.rules import (
    OverrideTarget,
    PackageType,
    ProductCategory,
    Rule7Route,
    SectorRoutedError,
    Verdict,
    controlling_framework,
    evaluate_rule7_height,
    evaluate_rule7_width,
    load_rules,
    minimum_character_height,
    pdp_declaration_mandatory,
    rule_33_relaxation_applies,
    sector_overrides,
)

TODAY = date(2026, 9, 6)
BEFORE_GSR_778E = date(2025, 10, 23)


# --- medical devices: a carve-out, not a stricter path -----------------------------------


def test_a_medical_device_does_not_get_table_i_from_the_public_lookup() -> None:
    """The bug this ticket fixes: a sector-blind lookup silently applying Table-I.

    ``minimum_character_height`` is exported, so guarding only the two evaluators that
    call it would leave every other caller applying a Rule 7 band to a package the rule
    does not reach.
    """
    with pytest.raises(SectorRoutedError, match="Medical Devices Rules, 2017"):
        minimum_character_height(
            Decimal("120"),
            is_blown_formed_or_moulded=False,
            product_category=ProductCategory.MEDICAL_DEVICE,
            evaluation_date=TODAY,
        )


def test_a_medical_device_height_evaluation_states_no_millimetre_requirement() -> None:
    """No Medical Devices Rules, 2017 thresholds are encoded, so none may be produced."""
    evaluation = evaluate_rule7_height(
        panel_area=Decimal("120"),
        measured_height=Decimal("0.2"),
        is_blown_formed_or_moulded=False,
        product_category=ProductCategory.MEDICAL_DEVICE,
        evaluation_date=TODAY,
    )

    assert evaluation.route is Rule7Route.SECTOR_FRAMEWORK
    assert evaluation.verdict is Verdict.REVIEW
    assert evaluation.required_height_mm is None
    assert evaluation.override is not None
    assert evaluation.override.controlling_framework == "Medical Devices Rules, 2017"
    assert evaluation.override.rule_id == "R7-MEDICAL-DEVICE-OVERRIDE"


def test_a_medical_device_measured_below_table_i_is_not_a_violation() -> None:
    """A height that would fail Table-I is not a finding when Table-I does not apply.

    0.2 mm on a 120 cm2 panel is far under the 2.5 mm band. An ordinary package is a
    POTENTIAL VIOLATION on those numbers; a medical device is REVIEW, because the
    packaged rules have nothing to say about it.
    """
    ordinary = evaluate_rule7_height(
        panel_area=Decimal("120"),
        measured_height=Decimal("0.2"),
        is_blown_formed_or_moulded=False,
        product_category=None,
        evaluation_date=TODAY,
    )
    medical = evaluate_rule7_height(
        panel_area=Decimal("120"),
        measured_height=Decimal("0.2"),
        is_blown_formed_or_moulded=False,
        product_category=ProductCategory.MEDICAL_DEVICE,
        evaluation_date=TODAY,
    )

    assert ordinary.verdict is Verdict.POTENTIAL_VIOLATION
    assert ordinary.required_height_mm == Decimal("2.5")
    assert medical.verdict is Verdict.REVIEW


def test_a_medical_device_width_evaluation_routes_to_the_mdr() -> None:
    evaluation = evaluate_rule7_width(
        character="8",
        width=Decimal("0.1"),
        height=Decimal("4"),
        product_category=ProductCategory.MEDICAL_DEVICE,
        evaluation_date=TODAY,
    )

    assert evaluation.route is Rule7Route.SECTOR_FRAMEWORK
    assert evaluation.verdict is Verdict.REVIEW
    assert evaluation.ratio_result is None


def test_the_rule_33_relaxation_is_disapplied_for_medical_devices() -> None:
    """G.S.R. 778(E) paragraph 4 removes the relaxation where the MDR applies."""
    assert rule_33_relaxation_applies(ProductCategory.MEDICAL_DEVICE, TODAY) is False
    assert rule_33_relaxation_applies(ProductCategory.FOOD, TODAY) is True
    assert rule_33_relaxation_applies(None, TODAY) is True


def test_the_pdp_declaration_is_not_mandatory_for_medical_devices() -> None:
    """Rule 2(h) is routed to the MDR, so the packaged rules stop mandating the panel."""
    assert pdp_declaration_mandatory(ProductCategory.MEDICAL_DEVICE, TODAY) is False
    assert pdp_declaration_mandatory(ProductCategory.COSMETICS, TODAY) is True
    assert pdp_declaration_mandatory(None, TODAY) is True


def test_the_medical_carve_out_does_not_reach_back_before_its_gazette() -> None:
    """A scan predating 24.10.2025 is adjudicated under the rules as they then stood."""
    assert sector_overrides(ProductCategory.MEDICAL_DEVICE, BEFORE_GSR_778E) == {}
    assert minimum_character_height(
        Decimal("120"),
        is_blown_formed_or_moulded=False,
        product_category=ProductCategory.MEDICAL_DEVICE,
        evaluation_date=BEFORE_GSR_778E,
    ) == Decimal("2.5")


# --- food and cosmetics ------------------------------------------------------------------


def test_a_food_product_routes_the_manufacturer_declaration_to_the_fssa() -> None:
    """Rule 6(1)(a) Explanation III disapplies the clause for food articles outright."""
    override = controlling_framework(
        OverrideTarget.MANUFACTURER_DECLARATION,
        ProductCategory.FOOD,
        TODAY,
    )

    assert override is not None
    assert override.controlling_framework == "Food Safety and Standards Act, 2006"
    assert override.rule_id == "R6-1-A-EXPL-III-FOOD"


def test_a_cosmetic_routes_the_date_declaration_to_the_drugs_and_cosmetics_rules() -> None:
    """The third proviso to Rule 6(1)(d) hands the date declaration to the 1945 Rules."""
    override = controlling_framework(
        OverrideTarget.DATE_DECLARATION,
        ProductCategory.COSMETICS,
        TODAY,
    )

    assert override is not None
    assert override.controlling_framework == "Drugs and Cosmetics Rules, 1945"
    assert override.rule_id == "R6-1-D-COSMETICS"


def test_a_sector_override_moves_only_the_obligations_it_names() -> None:
    """Food is routed for the manufacturer declaration and nothing else.

    A carve-out that leaked into neighbouring obligations would silently stop this
    module evaluating declarations it is still responsible for.
    """
    assert set(sector_overrides(ProductCategory.FOOD, TODAY)) == {
        OverrideTarget.MANUFACTURER_DECLARATION
    }
    assert set(sector_overrides(ProductCategory.COSMETICS, TODAY)) == {
        OverrideTarget.DATE_DECLARATION
    }
    assert set(sector_overrides(ProductCategory.MEDICAL_DEVICE, TODAY)) == {
        OverrideTarget.TABLE_HEIGHT,
        OverrideTarget.WIDTH_RATIO,
        OverrideTarget.PDP_DECLARATION,
    }


def test_food_and_cosmetics_still_measure_against_table_i() -> None:
    """Neither sector overrides character sizing, so nothing about Rule 7 changes."""
    for category in (ProductCategory.FOOD, ProductCategory.COSMETICS):
        assert minimum_character_height(
            Decimal("120"),
            is_blown_formed_or_moulded=False,
            product_category=category,
            evaluation_date=TODAY,
        ) == Decimal("2.5")


# --- dispatch shape ----------------------------------------------------------------------


def test_an_unconfirmed_category_routes_nothing() -> None:
    """Routing is keyed on a *confirmed* category; this module never infers one."""
    assert sector_overrides(None, TODAY) == {}
    assert controlling_framework(OverrideTarget.TABLE_HEIGHT, None, TODAY) is None


def test_the_dispatch_is_built_from_the_rule_store() -> None:
    """Adding a sector is a rule plus an enum member — no branch to extend.

    Every override the dispatch can return is traceable to a rule in the store, and every
    sector rule in the store is reachable through the dispatch. A hand-written branch
    would break one direction or the other.
    """
    encoded = {
        (rule.conditions.sector, target, rule.rule_id)
        for rule in load_rules()
        if rule.conditions.kind == "sector_override"
        for target in rule.conditions.overrides
    }
    dispatched = {
        (override.sector, override.target, override.rule_id)
        for category in ProductCategory
        for package_type in (None, *PackageType)
        for override in sector_overrides(category, TODAY, package_type=package_type).values()
    }

    assert dispatched == encoded


# --- package-type scoping ----------------------------------------------------------------


def test_an_unscoped_override_fires_for_every_package_type() -> None:
    """The three sector-wide overrides carry no package_type and must not have narrowed.

    Adding the scoping dimension for the Rule 2(kc) proviso must not have made the
    existing overrides conditional on a classification their gazettes never mention.
    """
    for package_type in (None, *PackageType):
        assert sector_overrides(
            ProductCategory.MEDICAL_DEVICE, TODAY, package_type=package_type
        ).keys() >= {OverrideTarget.TABLE_HEIGHT, OverrideTarget.WIDTH_RATIO}
        assert OverrideTarget.MANUFACTURER_DECLARATION in sector_overrides(
            ProductCategory.FOOD, TODAY, package_type=package_type
        )


def test_a_food_package_routes_to_the_fssa_with_no_package_type_confirmed() -> None:
    """Explanation III is unscoped: an ordinary food package still routes, unchanged."""
    overrides = sector_overrides(ProductCategory.FOOD, TODAY)

    assert set(overrides) == {OverrideTarget.MANUFACTURER_DECLARATION}
    routed = overrides[OverrideTarget.MANUFACTURER_DECLARATION]
    assert routed.controlling_framework == "Food Safety and Standards Act, 2006"
    assert routed.rule_id == "R6-1-A-EXPL-III-FOOD"


def test_only_a_multi_piece_food_package_picks_up_the_2kc_proviso() -> None:
    """The proviso is scoped to multi-piece packages and must not leak to the rest.

    Both routings name the same Act, so the rule id is what distinguishes them: the
    proviso is a second, narrower obligation sitting on top of Explanation III, not a
    restatement of it.
    """
    multi_piece = sector_overrides(
        ProductCategory.FOOD,
        TODAY,
        package_type=PackageType.MULTI_PIECE_PACKAGE,
    )

    assert set(multi_piece) == {
        OverrideTarget.MANUFACTURER_DECLARATION,
        OverrideTarget.PACKAGE_DEFINITION,
    }
    assert multi_piece[OverrideTarget.PACKAGE_DEFINITION].rule_id == "R2-KC-MULTI-PIECE-FOOD"
    assert (
        multi_piece[OverrideTarget.PACKAGE_DEFINITION].controlling_framework
        == "Food Safety and Standards Act, 2006"
    )

    for package_type in (None, PackageType.GROUP_PACKAGE, PackageType.COMBINATION_PACKAGE):
        assert OverrideTarget.PACKAGE_DEFINITION not in sector_overrides(
            ProductCategory.FOOD, TODAY, package_type=package_type
        )


def test_the_2kc_proviso_does_not_reach_a_non_food_multi_piece_package() -> None:
    """Soap cakes are the gazette's own illustration, and soap is not a food article."""
    for category in (ProductCategory.COSMETICS, ProductCategory.MEDICAL_DEVICE, None):
        assert OverrideTarget.PACKAGE_DEFINITION not in sector_overrides(
            category, TODAY, package_type=PackageType.MULTI_PIECE_PACKAGE
        )
