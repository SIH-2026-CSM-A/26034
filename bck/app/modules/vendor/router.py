"""The vendor register endpoints. Read-only, and thin.

Two routes, both reads. There is no POST here: a vendor row is written by
:func:`~app.modules.vendor.repository.persist_vendor_scan` as part of attributing a scan,
which is the only thing that knows a premises exists. A create route would be a second way
onto the register with nothing to attribute.

**Authorisation is here, not in the interface.** Both reads go through the repository, which
applies :func:`~app.modules.vendor.service.scope_vendor_query` to every statement. A vendor
outside the caller's jurisdiction is a 404 — the same answer as one that is not on the
register, because a 403 would confirm to an officer in one state that a premises in another
is known to the department.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import Principal, get_current_principal, get_session
from app.modules.vendor import repository
from app.modules.vendor.schemas import VendorResponse, vendor_response

vendor_router = APIRouter(prefix="/vendors", tags=["vendors"])

Session = Annotated[AsyncSession, Depends(get_session)]
Officer = Annotated[Principal, Depends(get_current_principal)]


@vendor_router.get("")
async def list_vendors(session: Session, principal: Officer) -> list[VendorResponse]:
    """Vendors this officer may see, by name.

    The jurisdiction predicate is applied by the repository on every query and is not
    something a caller can widen — there is no jurisdiction parameter on this route.
    """
    return [vendor_response(row) for row in await repository.list_vendors(session, principal)]


@vendor_router.get("/{vendor_id}")
async def get_vendor(vendor_id: UUID, session: Session, principal: Officer) -> VendorResponse:
    """One vendor in full, or a 404 for absent and out-of-jurisdiction alike."""
    row = await repository.get_scoped_vendor(session, vendor_id, principal)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="vendor not found")
    return vendor_response(row)
