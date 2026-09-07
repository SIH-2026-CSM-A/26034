"""Analytics policy and response mapping.

``K_ANONYMITY_MIN_COHORT`` and the density bands are uncalibrated priors. A cohort of
three prevents a singleton or pair from appearing as an aggregate cell, but does not
guarantee anonymity. It is a prototype privacy floor that must be calibrated against
deployment privacy requirements before it is presented as production policy.

Density bands describe relative counts in the observed, privacy-suppressed result set.
They are not calibrated risk statistics and must be recalibrated against deployment data.
"""

from collections.abc import Iterable
from datetime import date
from enum import StrEnum

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.analytics import repository
from app.modules.analytics.constants import K_ANONYMITY_MIN_COHORT
from app.modules.analytics.schemas import (
    CategoryAggregateCell,
    DailyAggregateCell,
    JurisdictionAggregateCell,
    RuleAggregateCell,
)

TERTILE_DIVISOR = 3
"""The number of relative density ranges in the uncalibrated display policy."""

UPPER_TERTILE_MULTIPLIER = 2
"""The numerator locating the upper tertile boundary in sorted observed counts."""

UNCONFIRMED_CATEGORY_BUCKET = "UNCONFIRMED"
"""Display-only bucket for a scan whose confirmed product category is absent."""


class DensityBand(StrEnum):
    """A relative density display band, not a calibrated risk classification."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


def density_bands(counts: Iterable[int]) -> dict[int, DensityBand]:
    """Assign deterministic relative density bands to observed, eligible cohort counts."""
    observed_counts = sorted(counts)
    distinct_counts = sorted(set(observed_counts))
    if not distinct_counts:
        return {}
    if len(distinct_counts) == 1:
        return {distinct_counts[0]: DensityBand.MEDIUM}
    if len(distinct_counts) == 2:
        return {
            distinct_counts[0]: DensityBand.LOW,
            distinct_counts[1]: DensityBand.HIGH,
        }

    final_index = len(observed_counts) - 1
    lower_cut_point = observed_counts[final_index // TERTILE_DIVISOR]
    upper_cut_point = observed_counts[
        (final_index * UPPER_TERTILE_MULTIPLIER + TERTILE_DIVISOR - 1) // TERTILE_DIVISOR
    ]
    return {
        count: (
            DensityBand.LOW
            if count <= lower_cut_point
            else DensityBand.HIGH
            if count >= upper_cut_point
            else DensityBand.MEDIUM
        )
        for count in distinct_counts
    }


def category_cells(
    rows: Iterable[tuple[str | None, int]],
) -> list[CategoryAggregateCell]:
    """Map privacy-eligible category counts without inferring a missing category."""
    return [
        CategoryAggregateCell(
            product_category=UNCONFIRMED_CATEGORY_BUCKET if category is None else category,
            count=count,
        )
        for category, count in rows
        if count >= K_ANONYMITY_MIN_COHORT
    ]


def rule_cells(rows: Iterable[tuple[str, int]]) -> list[RuleAggregateCell]:
    """Map privacy-eligible rule counts in deterministic dashboard order."""
    eligible_rows = ((rule_id, count) for rule_id, count in rows if count >= K_ANONYMITY_MIN_COHORT)
    return [
        RuleAggregateCell(rule_id=rule_id, count=count)
        for rule_id, count in sorted(eligible_rows, key=lambda row: (-row[1], row[0]))
    ]


def daily_cells(rows: Iterable[tuple[date, int]]) -> list[DailyAggregateCell]:
    """Map privacy-eligible verdict-day counts in chronological order."""
    eligible_rows = (row for row in rows if row[1] >= K_ANONYMITY_MIN_COHORT)
    return [DailyAggregateCell(day=day, count=count) for day, count in sorted(eligible_rows)]


def jurisdiction_cells(
    rows: Iterable[tuple[str, str | None, str | None, int]],
) -> list[JurisdictionAggregateCell]:
    """Map privacy-eligible jurisdiction counts with relative density display bands."""
    eligible_rows = [row for row in rows if row[3] >= K_ANONYMITY_MIN_COHORT]
    bands_by_count = density_bands(row[3] for row in eligible_rows)
    return [
        JurisdictionAggregateCell(
            state=state,
            region=region,
            district=district,
            count=count,
            density_band=bands_by_count[count],
        )
        for state, region, district, count in eligible_rows
    ]


async def by_rule(session: AsyncSession) -> list[RuleAggregateCell]:
    """Load and map privacy-eligible failing-finding cohorts by rule identifier."""
    return rule_cells(await repository.rule_counts(session))


async def by_category(session: AsyncSession) -> list[CategoryAggregateCell]:
    """Load and map privacy-eligible potential-verdict cohorts by category."""
    return category_cells(await repository.category_counts(session))


async def over_time(session: AsyncSession) -> list[DailyAggregateCell]:
    """Load and map privacy-eligible potential-verdict cohorts by evaluation day."""
    return daily_cells(await repository.daily_counts(session))


async def by_jurisdiction(session: AsyncSession) -> list[JurisdictionAggregateCell]:
    """Load and map privacy-eligible potential-verdict cohorts by jurisdiction."""
    return jurisdiction_cells(await repository.jurisdiction_counts(session))
