"""The complaint endpoints. Thin: parse in, delegate, return out.

**The officer is the principal, never the payload.** ``raised_by_officer_id`` is written
from :attr:`~app.core.rbac.Principal.subject` on every row this router creates, and
:class:`~app.modules.complaints.schemas.ComplaintRaiseRequest` forbids unknown fields, so
there is no shape of request that can name a different officer.

**Append-only, here as everywhere else.** There is no PUT and no DELETE on this router, and
:func:`raise_complaint` writes a new row whose ``supersedes_id`` names the current head of
the scan's thread — resolved from storage rather than supplied, because a caller choosing
what their row supersedes is a caller rewriting the history it supersedes.

**Authorisation is here, not in the interface.** Every read goes through the repository,
which joins to the scan and scopes to the caller's jurisdiction; a complaint outside it is a
404, the same answer as one that does not exist.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import Principal, get_current_principal, get_session
from app.modules.complaints import repository
from app.modules.complaints.domain import UnconfirmedVerdictError
from app.modules.complaints.schemas import (
    ComplaintRaiseRequest,
    ComplaintResponse,
    ComplaintThread,
    complaint_response,
)
from app.modules.complaints.service import ComplaintService

complaints_router = APIRouter(prefix="/complaints", tags=["complaints"])

Session = Annotated[AsyncSession, Depends(get_session)]
Officer = Annotated[Principal, Depends(get_current_principal)]

_service = ComplaintService()
"""The service holds no state and opens no connection, so one instance is the whole need."""


@complaints_router.get("")
async def list_complaints(session: Session, principal: Officer) -> list[ComplaintResponse]:
    """Complaint rows this officer may see, newest first.

    The jurisdiction predicate is applied by the repository on every query and is not
    something a caller can widen — there is no jurisdiction parameter on this route.
    """
    records = await repository.list_complaints(session, principal)
    return [complaint_response(record) for record in records]


@complaints_router.post("", status_code=status.HTTP_201_CREATED)
async def raise_complaint(
    body: ComplaintRaiseRequest, session: Session, principal: Officer
) -> ComplaintResponse:
    """Open an escalation against the manufacturer named on a scan's confirmed verdict.

    Three refusals, and they mean different things. A scan this officer cannot see is a 404.
    A scan no officer has finalised, or one whose effective verdict is not
    POTENTIAL_VIOLATION, is a 409 — the scan is real and visible, and there is simply
    nothing here to escalate yet. Text that would put a legal determination in an
    external-facing summary is a 422 against the request that carried it.
    """
    # One transaction for the reads and the write, matching the review route: the complaint
    # must be recorded against the verdict and the thread head that were read for it, not
    # against whatever a second transaction would find.
    async with session.begin():
        if await repository.get_scoped_scan_id(session, body.scan_id, principal) is None:
            raise _not_found()

        try:
            confirmed = await repository.confirmed_verdict_for_scan(session, body.scan_id)
        except UnconfirmedVerdictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        if confirmed is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="this scan has no finalising officer review to escalate",
            )

        try:
            record = _service.raise_complaint(
                confirmed_verdict=confirmed,
                manufacturer_name=body.manufacturer_name,
                rule_id=body.rule_id,
                field=body.field,
                measured_value=body.measured_value,
                required_value=body.required_value,
                officer_id=principal.subject,
                prior_complaint=await repository.get_latest_complaint_for_scan(
                    session, body.scan_id
                ),
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
            ) from exc

        stored = await repository.add_complaint(session, record)

    return complaint_response(stored)


@complaints_router.get("/{complaint_id}")
async def get_complaint(
    complaint_id: UUID, session: Session, principal: Officer
) -> ComplaintThread:
    """One complaint, with the escalation history recorded against its scan.

    The history is every complaint row for that scan, oldest first — which is what the table
    holds. Reconstructing separate threads out of the ``supersedes_id`` chains is a reading
    the caller can make from the rows; it is not one this route makes for them.
    """
    record = await repository.get_scoped_complaint(session, complaint_id, principal)
    if record is None:
        raise _not_found()

    history = await repository.get_complaints_for_scan(session, record.scan_id)
    return ComplaintThread(
        complaint=complaint_response(record),
        history=[complaint_response(entry) for entry in history],
    )


def _not_found() -> HTTPException:
    """The single answer for absent and out-of-jurisdiction alike."""
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="complaint not found")
