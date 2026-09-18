"""Reads and the one write the evidence surface makes, all scoped to the officer.

Every read goes through the same jurisdiction scoping the scan routes use, and for the same
reason: an evidence chain is a statement that a package in some district is under
examination, which is enforcement activity an officer elsewhere has no right to know of.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import Principal, scope_to_jurisdiction
from app.core.enums import ReviewAction
from app.core.models import EvidenceEntryRow, ReviewRow, Scan

from .domain import EvidenceEntry

FINALISING_ACTIONS = frozenset({ReviewAction.CONFIRM, ReviewAction.REJECT, ReviewAction.OVERRIDE})
"""The actions that end a review. A report may be produced only past one of these."""


async def get_scan(session: AsyncSession, scan_id: UUID, principal: Principal) -> Scan | None:
    """One scan, or ``None`` where it does not exist *or* is not this officer's to see."""
    statement = scope_to_jurisdiction(select(Scan), principal, Scan).where(Scan.id == scan_id)
    return (await session.scalars(statement)).one_or_none()


async def chain_for(session: AsyncSession, scan_id: UUID) -> list[EvidenceEntry]:
    """The scan's evidence chain, in sequence order, as the chain module models it.

    The payload comes back as the exact text that was hashed. ``payload_json`` holds the
    canonical bytes :func:`~app.modules.evidence.chain.compute_payload_hash` saw, and
    handing the string over unparsed is what lets verification recompute the same hash.
    """
    statement = (
        select(EvidenceEntryRow)
        .where(EvidenceEntryRow.scan_id == scan_id)
        .order_by(EvidenceEntryRow.sequence)
    )
    return [
        EvidenceEntry(
            sequence=row.sequence,
            timestamp=row.timestamp,
            payload_hash=row.payload_hash,
            prev_hash=row.prev_hash,
            entry_hash=row.entry_hash,
            payload=row.payload_json,
            asset_type=row.asset_type,
        )
        for row in await session.scalars(statement)
    ]


async def finalising_review(session: AsyncSession, scan_id: UUID) -> ReviewRow | None:
    """The latest review that ended this scan's review, or ``None`` if none has."""
    statement = (
        select(ReviewRow)
        .where(ReviewRow.scan_id == scan_id, ReviewRow.action.in_(FINALISING_ACTIONS))
        .order_by(ReviewRow.created_at.desc())
        .limit(1)
    )
    return (await session.scalars(statement)).one_or_none()


def stage_entry(session: AsyncSession, scan_id: UUID, entry: EvidenceEntry) -> EvidenceEntryRow:
    """Stage one appended chain entry for the caller's transaction to commit."""
    row = EvidenceEntryRow(
        scan_id=scan_id,
        sequence=entry.sequence,
        timestamp=entry.timestamp,
        payload_hash=entry.payload_hash,
        prev_hash=entry.prev_hash,
        entry_hash=entry.entry_hash,
        payload_json=entry.payload if isinstance(entry.payload, str) else str(entry.payload),
        asset_type=entry.asset_type,
    )
    session.add(row)
    return row
