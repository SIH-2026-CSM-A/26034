"""Analytics aggregate behavior."""

import ast
from datetime import date
from pathlib import Path

from app.modules.analytics import router, service

ANALYTICS_MODULE_DIRECTORY = Path(__file__).resolve().parents[3] / "app" / "modules" / "analytics"


def test_analytics_router_uses_the_analytics_prefix() -> None:
    """The integration layer receives a self-contained analytics router."""
    assert router.analytics_router.prefix == "/analytics"


def test_density_bands_assign_medium_to_a_single_observed_count() -> None:
    """A single surviving count has no relative lower or upper density."""
    assert service.density_bands((3, 3, 3)) == {3: "MEDIUM"}


def test_density_bands_assign_low_and_high_to_two_observed_counts() -> None:
    """Two distinct surviving counts map to the two outer density bands."""
    assert service.density_bands((3, 3, 8, 8)) == {3: "LOW", 8: "HIGH"}


def test_density_bands_use_tie_safe_tertiles_for_three_or_more_counts() -> None:
    """Equal counts never divide across bands at a tertile boundary."""
    assert service.density_bands((3, 3, 4, 5, 6, 6, 7)) == {
        3: "LOW",
        4: "LOW",
        5: "MEDIUM",
        6: "HIGH",
        7: "HIGH",
    }


def test_category_cells_map_only_null_categories_to_unconfirmed() -> None:
    """A missing confirmed category is displayed without inventing a category."""
    cells = service.category_cells(((None, 3), ("food", 3), ("cosmetics", 2)))

    assert [(cell.product_category, cell.count) for cell in cells] == [
        ("UNCONFIRMED", 3),
        ("food", 3),
    ]


def test_rule_cells_suppress_small_distinct_scan_cohorts() -> None:
    """Rule cells below the privacy floor are never made available to callers."""
    cells = service.rule_cells((("RULE-6-1-A", 3), ("RULE-6-1-C", 2)))

    assert [(cell.rule_id, cell.count) for cell in cells] == [("RULE-6-1-A", 3)]


def test_daily_cells_keep_privacy_eligible_days_in_chronological_order() -> None:
    """Day results preserve the repository's calendar buckets without small cohorts."""
    cells = service.daily_cells(
        ((date(2026, 9, 8), 3), (date(2026, 9, 7), 2), (date(2026, 9, 6), 4))
    )

    assert [(cell.day, cell.count) for cell in cells] == [
        (date(2026, 9, 6), 4),
        (date(2026, 9, 8), 3),
    ]


def test_jurisdiction_cells_exclude_suppressed_counts_from_density_bands() -> None:
    """A small district cannot affect visible density bands or appear itself."""
    cells = service.jurisdiction_cells(
        (
            ("Maharashtra", "Pune", "Satara", 3),
            ("Maharashtra", "Pune", "Pune", 6),
            ("Maharashtra", "Pune", "Baramati", 2),
        )
    )

    assert [(cell.district, cell.count, cell.density_band) for cell in cells] == [
        ("Satara", 3, "LOW"),
        ("Pune", 6, "HIGH"),
    ]


def test_aggregate_cell_mappers_return_empty_results_for_no_rows() -> None:
    """An empty persistence result stays empty at the API boundary."""
    assert service.rule_cells(()) == []
    assert service.category_cells(()) == []
    assert service.daily_cells(()) == []
    assert service.jurisdiction_cells(()) == []


def test_aggregate_cell_mappers_suppress_singleton_cohorts() -> None:
    """Every aggregate shape excludes a cohort that identifies one scan."""
    day = date(2026, 9, 8)

    assert service.rule_cells((("RULE-SINGLETON", 1),)) == []
    assert service.category_cells((("food", 1),)) == []
    assert service.daily_cells(((day, 1),)) == []
    assert service.jurisdiction_cells((("Maharashtra", "Pune", "Satara", 1),)) == []


def test_analytics_imports_only_core_contracts_or_its_own_module() -> None:
    """A feature-module import cannot bypass the analytics integration boundary."""
    for source_path in ANALYTICS_MODULE_DIRECTORY.glob("*.py"):
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        imported_modules = [
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module is not None
        ]
        assert all(
            module.startswith(("app.core", "app.contracts", "app.modules.analytics"))
            for module in imported_modules
            if module.startswith("app.")
        ), source_path
