"""Database-backed tests for privacy-suppressed analytics queries."""

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts import DeclarationField, FieldState, Verdict
from app.core import (
    CalibrationMethod,
    FieldFindingRow,
    Jurisdiction,
    Principal,
    RoleTier,
    Scan,
    ScanSourceType,
    ScanStatus,
    VerdictRow,
)
from app.modules.analytics import repository

pytestmark = pytest.mark.postgres

CONTROLLER = Principal(
    subject="controller-mh", tier=RoleTier.STATE, jurisdiction=Jurisdiction(state="Maharashtra")
)
"""A state officer over the state every fixture scan defaults to."""

SATARA_INSPECTOR = Principal(
    subject="inspector-satara",
    tier=RoleTier.DISTRICT,
    jurisdiction=Jurisdiction(state="Maharashtra", region="Pune", district="Satara"),
)


async def add_scan_with_verdict(
    session: AsyncSession,
    *,
    state: str = "Maharashtra",
    region: str | None = "Pune",
    district: str | None = "Satara",
    product_category: str | None = None,
    created_at: datetime,
    evaluated_at: datetime,
    verdict: Verdict = Verdict.POTENTIAL_VIOLATION,
    findings: tuple[tuple[str, FieldState, DeclarationField], ...] = (),
) -> Scan:
    """Persist one scan, one verdict, and its explicitly supplied field findings."""
    scan = Scan(
        source_type=ScanSourceType.CATALOGUE_RECORD,
        status=ScanStatus.COMPLETE,
        calibration_method=CalibrationMethod.NONE,
        state=state,
        region=region,
        district=district,
        officer_id="analytics-test-officer",
        rule_set_version="analytics-test-rules",
        product_category=product_category,
        image_refs=[],
        capture_metadata={},
        created_at=created_at,
    )
    session.add(scan)
    await session.flush()
    verdict_row = VerdictRow(
        scan_id=scan.id,
        verdict=verdict,
        subject_ref=str(scan.id),
        rule_set_version="analytics-test-rules",
        evaluated_at=evaluated_at,
        field_providers={},
    )
    session.add(verdict_row)
    await session.flush()
    session.add_all(
        FieldFindingRow(
            verdict_id=verdict_row.id,
            field=field,
            rule_id=rule_id,
            state=finding_state,
            reason="analytics test finding",
            rule_snapshot={"rule_id": rule_id},
            evidence_span_ids=[],
            evidence_regions=[],
        )
        for rule_id, finding_state, field in findings
    )
    await session.commit()
    return scan


async def test_rule_counts_distinct_scans_with_failing_findings(session: AsyncSession) -> None:
    """Multiple failing findings on one scan count once for a rule cohort."""
    timestamp = datetime(2026, 9, 8, 9, tzinfo=UTC)
    await add_scan_with_verdict(
        session,
        created_at=timestamp,
        evaluated_at=timestamp,
        findings=(
            ("RULE-ELIGIBLE", FieldState.FAIL, DeclarationField.NET_QUANTITY),
            ("RULE-ELIGIBLE", FieldState.FAIL, DeclarationField.RETAIL_SALE_PRICE),
            ("RULE-PASS", FieldState.PASS, DeclarationField.COMMON_OR_GENERIC_NAME),
        ),
    )
    for field in (DeclarationField.CONSUMER_CARE, DeclarationField.DIMENSIONS):
        await add_scan_with_verdict(
            session,
            created_at=timestamp,
            evaluated_at=timestamp,
            findings=(("RULE-ELIGIBLE", FieldState.FAIL, field),),
        )
    for field in (DeclarationField.NET_QUANTITY, DeclarationField.RETAIL_SALE_PRICE):
        await add_scan_with_verdict(
            session,
            created_at=timestamp,
            evaluated_at=timestamp,
            findings=(("RULE-SUPPRESSED", FieldState.FAIL, field),),
        )

    assert await repository.rule_counts(session, CONTROLLER) == [("RULE-ELIGIBLE", 3)]


async def test_category_counts_keep_null_as_a_real_privacy_cohort(session: AsyncSession) -> None:
    """Missing confirmed categories group separately and receive the same privacy floor."""
    timestamp = datetime(2026, 9, 8, 9, tzinfo=UTC)
    for _ in range(3):
        await add_scan_with_verdict(
            session,
            created_at=timestamp,
            evaluated_at=timestamp,
            product_category=None,
        )
    for _ in range(3):
        await add_scan_with_verdict(
            session,
            created_at=timestamp,
            evaluated_at=timestamp,
            product_category="food",
        )
    for _ in range(2):
        await add_scan_with_verdict(
            session,
            created_at=timestamp,
            evaluated_at=timestamp,
            product_category="cosmetics",
        )

    assert await repository.category_counts(session, CONTROLLER) == [(None, 3), ("food", 3)]


async def test_daily_counts_use_verdict_evaluation_day(session: AsyncSession) -> None:
    """Verdict buckets do not substitute the earlier scan-creation timestamp."""
    created_at = datetime(2026, 9, 1, 9, tzinfo=UTC)
    evaluated_at = datetime(2026, 9, 8, 1, tzinfo=UTC)
    for _ in range(3):
        await add_scan_with_verdict(
            session,
            created_at=created_at,
            evaluated_at=evaluated_at,
        )

    assert await repository.daily_counts(session, CONTROLLER) == [(evaluated_at.date(), 3)]


async def test_jurisdiction_counts_use_scan_geography_not_finding_state(
    session: AsyncSession,
) -> None:
    """Heatmap geography comes only from Scan state, region, and district columns."""
    timestamp = datetime(2026, 9, 8, 9, tzinfo=UTC)
    for _ in range(3):
        await add_scan_with_verdict(
            session,
            state="Maharashtra",
            region="Pune",
            district="Satara",
            created_at=timestamp,
            evaluated_at=timestamp,
            findings=(("RULE-HEATMAP", FieldState.FAIL, DeclarationField.NET_QUANTITY),),
        )
    for _ in range(2):
        await add_scan_with_verdict(
            session,
            state="Karnataka",
            region="Mysuru",
            district="Mysuru",
            created_at=timestamp,
            evaluated_at=timestamp,
        )

    assert await repository.jurisdiction_counts(session, CONTROLLER) == [
        ("Maharashtra", "Pune", "Satara", 3)
    ]


async def test_every_aggregate_is_scoped_to_the_callers_jurisdiction(
    session: AsyncSession,
) -> None:
    """A district officer's aggregates count their district and nothing beside it.

    Three eligible scans in Satara and three in Kolhapur. The controller above both sees
    six; the Satara inspector sees three in every aggregate, as a WHERE clause on the scan.
    """
    timestamp = datetime(2026, 9, 8, 9, tzinfo=UTC)
    for district in ("Satara", "Kolhapur"):
        for _ in range(3):
            await add_scan_with_verdict(
                session,
                district=district,
                created_at=timestamp,
                evaluated_at=timestamp,
                findings=(("RULE-SCOPED", FieldState.FAIL, DeclarationField.NET_QUANTITY),),
            )

    assert await repository.rule_counts(session, CONTROLLER) == [("RULE-SCOPED", 6)]
    assert await repository.rule_counts(session, SATARA_INSPECTOR) == [("RULE-SCOPED", 3)]
    assert await repository.category_counts(session, SATARA_INSPECTOR) == [(None, 3)]
    assert await repository.daily_counts(session, SATARA_INSPECTOR) == [(timestamp.date(), 3)]
    assert await repository.jurisdiction_counts(session, SATARA_INSPECTOR) == [
        ("Maharashtra", "Pune", "Satara", 3)
    ]
