"""Vendor persistence and jurisdiction lookup repository under VND-001 Part B.

Provides minimal read/write persistence for vendor self-scan submissions:
1. Persisting a VendorSubmission as a vendor_scans row against an existing scan.
2. Looking up a vendor's jurisdiction by vendor_id for routing via route_verdict.

Session management follows the codebase convention: one session per request,
transaction committed by the caller.

Import rule: vendor/ may import from app.contracts, app.core, and itself.
Nothing from pipeline, no other modules, and no tables related to complaints
or product reviews.
"""

import inspect
from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core import (
    Jurisdiction,
    Principal,
    VendorRow,
    VendorScanRow,
)
from app.modules.vendor.domain import VendorSubmission
from app.modules.vendor.service import scope_vendor_query


async def _get(session: AsyncSession | Session, model: type[Any], pk: Any) -> Any:
    """Retrieve an entity by primary key, awaiting if the session is async."""
    res = session.get(model, pk)
    if inspect.isawaitable(res):
        return await res
    return res


async def _flush(session: AsyncSession | Session) -> None:
    """Flush pending changes to the database, awaiting if the session is async."""
    res = session.flush()
    if inspect.isawaitable(res):
        await res


async def persist_vendor_scan(
    session: AsyncSession | Session,
    scan_id: UUID,
    submission: VendorSubmission,
) -> VendorScanRow:
    """Persist a VendorSubmission as a vendor_scans row against an existing scan.

    If the vendor does not exist in the vendors table yet, creates and stages the
    VendorRow first (flushing so the parent exists for the foreign key constraint).
    Then stages the VendorScanRow attributing the scan to the vendor.

    The session is NOT committed here; transaction ownership belongs to the caller.

    Parameters
    ----------
    session : AsyncSession | Session
        Database session for the request.
    scan_id : UUID
        The primary key of the existing scan being attributed.
    submission : VendorSubmission
        The vendor self-scan payload carrying vendor identity, trade classification,
        and jurisdiction.

    Returns
    -------
    VendorScanRow
        The staged attribution record linking the scan to the vendor.
    """
    vendor = await _get(session, VendorRow, submission.id)
    if vendor is None:
        vendor = VendorRow(
            id=submission.id,
            name=submission.name,
            vendor_type=submission.vendor_type,
            state=submission.state,
            region=submission.region,
            district=submission.district,
        )
        session.add(vendor)
        await _flush(session)

    vendor_scan = VendorScanRow(
        scan_id=scan_id,
        vendor_id=submission.id,
    )
    session.add(vendor_scan)
    return vendor_scan


# Convenience aliases for caller naming conventions
record_vendor_scan = persist_vendor_scan
persist_vendor_submission = persist_vendor_scan
record_vendor_submission = persist_vendor_scan


async def get_vendor(
    session: AsyncSession | Session,
    vendor_id: UUID,
) -> VendorRow | None:
    """Look up a VendorRow by vendor_id, or None if not found."""
    return await _get(session, VendorRow, vendor_id)


async def get_vendor_jurisdiction(
    session: AsyncSession | Session,
    vendor_id: UUID,
) -> Jurisdiction | None:
    """Look up a vendor's jurisdiction by vendor_id for use in route_verdict.

    Parameters
    ----------
    session : AsyncSession | Session
        Database session for the request.
    vendor_id : UUID
        Unique identifier of the vendor.

    Returns
    -------
    Jurisdiction | None
        The reconstructed territorial jurisdiction of the vendor if found,
        or None if the vendor does not exist in storage.
    """
    vendor = await get_vendor(session, vendor_id)
    if vendor is None:
        return None
    return Jurisdiction(
        state=vendor.state,
        region=vendor.region,
        district=vendor.district,
    )


# Convenience alias for caller naming conventions
lookup_vendor_jurisdiction = get_vendor_jurisdiction


async def get_vendor_scan(
    session: AsyncSession | Session,
    scan_id: UUID,
) -> VendorScanRow | None:
    """Look up a VendorScanRow attribution by scan_id, or None if not found."""
    return await _get(session, VendorScanRow, scan_id)


__all__ = [
    "get_scoped_vendor",
    "get_vendor",
    "get_vendor_jurisdiction",
    "get_vendor_scan",
    "list_vendors",
    "lookup_vendor_jurisdiction",
    "persist_vendor_scan",
    "persist_vendor_submission",
    "record_vendor_scan",
    "record_vendor_submission",
]


async def list_vendors(session: AsyncSession, principal: Principal) -> Sequence[VendorRow]:
    """Every vendor inside this officer's jurisdiction, by name.

    The territorial predicate is applied here rather than by the caller, for the reason
    :func:`app.modules.vendor.service.scope_vendor_query` names as its own ceiling: a caller
    that forgets to scope is not scoped, and no permission check elsewhere catches it. There
    is no jurisdiction parameter on the route above this, so there is nothing for a caller
    to widen.
    """
    statement = scope_vendor_query(select(VendorRow), principal, VendorRow).order_by(
        VendorRow.name.asc(), VendorRow.id.asc()
    )
    return (await session.scalars(statement)).all()


async def get_scoped_vendor(
    session: AsyncSession, vendor_id: UUID, principal: Principal
) -> VendorRow | None:
    """One vendor, or ``None`` where it does not exist *or* is not this officer's to see.

    Deliberately one answer for both. Distinguishing them would confirm to an officer in one
    state that a premises in another is on the register, which is the same disclosure
    :func:`app.pipeline.repository.get_scan` refuses to make about a scan.

    Note what the nullability of the jurisdiction columns means here, because it is
    counter-intuitive: ``NULL = 'Satara'`` is never true, so a vendor recorded with no
    district is invisible to a district officer while remaining visible to the state officer
    above them. A NULL says the level was never recorded, not that it matches everything.
    """
    statement = scope_vendor_query(select(VendorRow), principal, VendorRow).where(
        VendorRow.id == vendor_id
    )
    return (await session.scalars(statement)).one_or_none()
