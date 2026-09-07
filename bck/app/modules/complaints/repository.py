"""Persistence repository for manufacturer complaints (CMP-001 Part B)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.complaints import ComplaintRow
from app.modules.complaints.domain import ComplaintRecord, ComplaintStatus


def _row_to_record(row: ComplaintRow) -> ComplaintRecord:
    """Convert an ORM ComplaintRow to a pure domain ComplaintRecord."""
    raw_status = row.status.value if hasattr(row.status, "value") else str(row.status)
    return ComplaintRecord(
        id=row.id,
        scan_id=row.scan_id,
        verdict_id=row.verdict_id,
        manufacturer_name=row.manufacturer_name,
        issue_summary=row.issue_summary,
        status=ComplaintStatus(raw_status),
        raised_by_officer_id=row.raised_by_officer_id,
        raised_at=row.raised_at,
        supersedes_id=row.supersedes_id,
    )


def _record_to_row(record: ComplaintRecord) -> ComplaintRow:
    """Convert a pure domain ComplaintRecord to an ORM ComplaintRow."""
    return ComplaintRow(
        id=record.id,
        scan_id=record.scan_id,
        verdict_id=record.verdict_id,
        manufacturer_name=record.manufacturer_name,
        issue_summary=record.issue_summary,
        status=record.status,
        raised_by_officer_id=record.raised_by_officer_id,
        raised_at=record.raised_at,
        supersedes_id=record.supersedes_id,
    )


async def add_complaint(session: AsyncSession, record: ComplaintRecord) -> ComplaintRecord:
    """Stage and persist a new complaint row into the database session."""
    row = _record_to_row(record)
    session.add(row)
    await session.flush()
    return _row_to_record(row)


async def get_complaint(session: AsyncSession, complaint_id: UUID) -> ComplaintRecord | None:
    """Retrieve a single complaint record by its primary key ID."""
    row = await session.get(ComplaintRow, complaint_id)
    if row is None:
        return None
    return _row_to_record(row)


async def get_complaints_for_scan(session: AsyncSession, scan_id: UUID) -> list[ComplaintRecord]:
    """Retrieve all complaint history rows for a scan ordered by raised_at ascending."""
    statement = (
        select(ComplaintRow)
        .where(ComplaintRow.scan_id == scan_id)
        .order_by(ComplaintRow.raised_at.asc(), ComplaintRow.id.asc())
    )
    result = await session.scalars(statement)
    return [_row_to_record(r) for r in result.all()]


async def get_latest_complaint_for_scan(
    session: AsyncSession, scan_id: UUID
) -> ComplaintRecord | None:
    """Retrieve the latest (head) complaint record in an escalation thread for a scan."""
    history = await get_complaints_for_scan(session, scan_id)
    if not history:
        return None

    superseded_ids = {c.supersedes_id for c in history if c.supersedes_id is not None}
    heads = [c for c in history if c.id not in superseded_ids]
    if heads:
        return heads[-1]
    return history[-1]
