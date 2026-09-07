"""Read-only SQL aggregate queries for analytics.

Each query counts distinct scan identities and applies the privacy floor in SQL. This
keeps suppressed cohorts inside the repository boundary rather than returning them for a
later layer to discard. Verdict rows are append-only, and these endpoints intentionally
aggregate evaluation activity across those rows; the distinct scan count prevents joined
duplicates from inflating any one aggregate cell.
"""

from datetime import date

from sqlalchemy import Date, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.contracts import FieldState, Verdict
from app.core import FieldFindingRow, Scan, VerdictRow
from app.modules.analytics.constants import K_ANONYMITY_MIN_COHORT


async def rule_counts(session: AsyncSession) -> list[tuple[str, int]]:
    """Return privacy-eligible distinct-scan cohorts for failing findings by rule."""
    finding_row = aliased(FieldFindingRow, name="finding")
    verdict_row = aliased(VerdictRow, name="verdict")
    scan_row = aliased(Scan, name="scan")
    cohort_count = func.count(func.distinct(scan_row.id)).label("count")
    statement = (
        select(finding_row.rule_id.label("rule_id"), cohort_count)
        .select_from(finding_row)
        .join(verdict_row, finding_row.verdict_id == verdict_row.id)
        .join(scan_row, verdict_row.scan_id == scan_row.id)
        .where(finding_row.state == FieldState.FAIL)
        .group_by(finding_row.rule_id)
        .having(cohort_count >= K_ANONYMITY_MIN_COHORT)
        .order_by(cohort_count.desc(), finding_row.rule_id.asc())
    )
    return [(rule_id, count) for rule_id, count in (await session.execute(statement)).tuples()]


async def category_counts(session: AsyncSession) -> list[tuple[str | None, int]]:
    """Return privacy-eligible distinct-scan cohorts by confirmed product category."""
    scan_row = aliased(Scan, name="scan")
    verdict_row = aliased(VerdictRow, name="verdict")
    cohort_count = func.count(func.distinct(scan_row.id)).label("count")
    statement = (
        select(scan_row.product_category.label("product_category"), cohort_count)
        .select_from(scan_row)
        .join(verdict_row, verdict_row.scan_id == scan_row.id)
        .where(verdict_row.verdict == Verdict.POTENTIAL_VIOLATION)
        .group_by(scan_row.product_category)
        .having(cohort_count >= K_ANONYMITY_MIN_COHORT)
        .order_by(cohort_count.desc(), scan_row.product_category.asc().nullsfirst())
    )
    return [(category, count) for category, count in (await session.execute(statement)).tuples()]


async def daily_counts(session: AsyncSession) -> list[tuple[date, int]]:
    """Return privacy-eligible potential-verdict scan cohorts by UTC evaluation day."""
    scan_row = aliased(Scan, name="scan")
    verdict_row = aliased(VerdictRow, name="verdict")
    evaluation_day = cast(func.timezone("UTC", verdict_row.evaluated_at), Date).label("day")
    cohort_count = func.count(func.distinct(scan_row.id)).label("count")
    statement = (
        select(evaluation_day, cohort_count)
        .select_from(verdict_row)
        .join(scan_row, verdict_row.scan_id == scan_row.id)
        .where(verdict_row.verdict == Verdict.POTENTIAL_VIOLATION)
        .group_by(evaluation_day)
        .having(cohort_count >= K_ANONYMITY_MIN_COHORT)
        .order_by(evaluation_day.asc())
    )
    return [(day, count) for day, count in (await session.execute(statement)).tuples()]


async def jurisdiction_counts(
    session: AsyncSession,
) -> list[tuple[str, str | None, str | None, int]]:
    """Return privacy-eligible potential-verdict cohorts by scan jurisdiction tuple."""
    scan_row = aliased(Scan, name="scan")
    verdict_row = aliased(VerdictRow, name="verdict")
    jurisdiction_state = scan_row.state.label("jurisdiction_state")
    jurisdiction_region = scan_row.region.label("jurisdiction_region")
    jurisdiction_district = scan_row.district.label("jurisdiction_district")
    cohort_count = func.count(func.distinct(scan_row.id)).label("count")
    statement = (
        select(jurisdiction_state, jurisdiction_region, jurisdiction_district, cohort_count)
        .select_from(scan_row)
        .join(verdict_row, verdict_row.scan_id == scan_row.id)
        .where(verdict_row.verdict == Verdict.POTENTIAL_VIOLATION)
        .group_by(jurisdiction_state, jurisdiction_region, jurisdiction_district)
        .having(cohort_count >= K_ANONYMITY_MIN_COHORT)
        .order_by(
            jurisdiction_state.asc(),
            jurisdiction_region.asc().nullsfirst(),
            jurisdiction_district.asc().nullsfirst(),
        )
    )
    return [
        (state, region, district, count)
        for state, region, district, count in (await session.execute(statement)).tuples()
    ]
