"""Persistence repository for manufacturer complaints (CMP-001 Part B)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts import FieldFinding, RuleParameterSnapshot, VerdictRecord
from app.core import FieldFindingRow, ReviewRow, Scan, VerdictRow
from app.core.complaints import ComplaintRow
from app.core.rbac import Principal, scope_to_jurisdiction
from app.modules.complaints.domain import (
    FINALISING_REVIEW_ACTIONS,
    ComplaintRecord,
    ComplaintStatus,
    ConfirmedVerdict,
)


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


def _scoped_complaints(principal: Principal) -> Select[Any]:
    """A SELECT over the complaints whose scan sits inside this principal's jurisdiction.

    ``complaints`` carries no territory of its own — a complaint is territorial because the
    scan it escalates is. The join is therefore the scoping, not a convenience: selecting
    from ``complaints`` alone would return every escalation in the country.
    """
    return scope_to_jurisdiction(
        select(ComplaintRow).join(Scan, ComplaintRow.scan_id == Scan.id), principal, Scan
    )


async def list_complaints(session: AsyncSession, principal: Principal) -> list[ComplaintRecord]:
    """Every complaint row this officer may see, newest first.

    Rows, not threads. The table is append-only, so a thread that has moved from RAISED to
    ACKNOWLEDGED is two rows here and both are returned — collapsing them to a head would
    be a decision this module makes nowhere else, and :attr:`ComplaintRecord.supersedes_id`
    is on every row for a caller that wants the shape.
    """
    statement = _scoped_complaints(principal).order_by(
        ComplaintRow.raised_at.desc(), ComplaintRow.id.asc()
    )
    return [_row_to_record(row) for row in (await session.scalars(statement)).all()]


async def get_scoped_complaint(
    session: AsyncSession, complaint_id: UUID, principal: Principal
) -> ComplaintRecord | None:
    """One complaint, or ``None`` where it does not exist *or* is not this officer's to see.

    One answer for both, for the reason :func:`app.pipeline.repository.get_scan` gives: a
    403 would confirm to an officer in one state that a manufacturer is under escalation in
    another.
    """
    statement = _scoped_complaints(principal).where(ComplaintRow.id == complaint_id)
    row = (await session.scalars(statement)).one_or_none()
    return None if row is None else _row_to_record(row)


async def get_scoped_scan_id(
    session: AsyncSession, scan_id: UUID, principal: Principal
) -> UUID | None:
    """``scan_id`` if that scan is inside this officer's jurisdiction, else ``None``."""
    statement = scope_to_jurisdiction(select(Scan.id), principal, Scan).where(Scan.id == scan_id)
    return (await session.scalars(statement)).one_or_none()


async def confirmed_verdict_for_scan(
    session: AsyncSession, scan_id: UUID
) -> ConfirmedVerdict | None:
    """The latest finalising review on a scan, paired with the verdict it names.

    ``None`` means no officer has confirmed, rejected or overridden anything here, which is
    the "nothing to escalate" case. A review that *does* exist but whose effective verdict
    is not POTENTIAL_VIOLATION is not filtered out on the way past: it reaches
    :class:`ConfirmedVerdict`, which refuses it. That refusal is the gate on complaint
    creation, and pre-empting it here would move the gate into a query.
    """
    statement = (
        select(ReviewRow)
        .where(ReviewRow.scan_id == scan_id)
        .where(ReviewRow.action.in_(FINALISING_REVIEW_ACTIONS))
        .order_by(ReviewRow.created_at.desc())
        .limit(1)
    )
    review = (await session.scalars(statement)).one_or_none()
    if review is None:
        return None

    verdict = await session.get(VerdictRow, review.verdict_id)
    if verdict is None:
        return None
    return ConfirmedVerdict(record=await _verdict_record(session, verdict), review_row=review)


async def _verdict_record(session: AsyncSession, verdict: VerdictRow) -> VerdictRecord:
    """One stored verdict and its findings back into the contract type.

    The ``model_validate`` round-trip on the snapshot is load-bearing for the same reason
    it is in :func:`app.pipeline.responses.finding_from_row`: snapshots are written with
    ``model_dump(mode="json")``, and a ``Decimal`` tolerance that came back as a float would
    silently misstate what the rule required of the manufacturer being escalated to.
    """
    statement = (
        select(FieldFindingRow)
        .where(FieldFindingRow.verdict_id == verdict.id)
        .order_by(FieldFindingRow.rule_id, FieldFindingRow.field)
    )
    return VerdictRecord(
        subject_ref=verdict.subject_ref,
        verdict=verdict.verdict,
        rule_set_version=verdict.rule_set_version,
        evaluated_at=verdict.evaluated_at,
        findings=tuple(
            FieldFinding(
                field=row.field,
                state=row.state,
                rule_snapshot=RuleParameterSnapshot.model_validate(row.rule_snapshot),
                observed_value=row.observed_value,
                expected_value=row.expected_value,
                reason=row.reason,
                evidence_span_ids=tuple(row.evidence_span_ids),
            )
            for row in (await session.scalars(statement)).all()
        ),
        field_providers=verdict.field_providers,
    )
