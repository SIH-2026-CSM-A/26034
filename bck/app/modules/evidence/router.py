"""The evidence surface: a chain verified on every read, and a report past a human gate.

Mounted by ``app.main`` like every other module router. Both routes are officer-only and
jurisdiction-scoped through the same predicate the scan routes use; a scan outside the
officer's jurisdiction is a 404, never a 403, so that its existence is not disclosed.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import Principal, get_current_principal, get_session

from . import repository, service
from .report import UnconfirmedVerdictExportError
from .schemas import EntrySummary, EvidenceView

evidence_router = APIRouter(prefix="/scans", tags=["evidence"])

Session = Annotated[AsyncSession, Depends(get_session)]
Officer = Annotated[Principal, Depends(get_current_principal)]


async def _scan_or_404(session: AsyncSession, scan_id: UUID, principal: Principal):
    scan = await repository.get_scan(session, scan_id, principal)
    if scan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="scan not found")
    return scan


@evidence_router.get("/{scan_id}/evidence", response_model=EvidenceView)
async def read_evidence(scan_id: UUID, session: Session, principal: Officer) -> EvidenceView:
    """The scan's evidence chain, verified now, on this read."""
    scan = await _scan_or_404(session, scan_id, principal)
    entries = await repository.chain_for(session, scan.id)
    return EvidenceView(
        scan_id=str(scan.id),
        verification=service.verified(entries),
        entries=[
            EntrySummary(
                sequence=entry.sequence,
                timestamp=entry.timestamp,
                entry_hash=entry.entry_hash,
                asset_type=entry.asset_type,
                is_purged=entry.is_purged,
            )
            for entry in entries
        ],
    )


@evidence_router.post("/{scan_id}/evidence/report", status_code=status.HTTP_201_CREATED)
async def export_report(
    scan_id: UUID, session: Session, principal: Officer, format: str = "json"
) -> Response:
    """Issue the BSA s.63(4) Part A certificate (``json``) or the filed report (``pdf``, ``docx``).

    A POST, because issuing a report is an event the chain records: the export's digest and
    the officer who took it are appended as the next entry. Refused with 409 until an
    officer has finalised the review, and refused outright if the chain does not verify.
    """
    if format not in service.REPORT_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"format must be one of {', '.join(service.REPORT_FORMATS)}",
        )
    scan = await _scan_or_404(session, scan_id, principal)
    entries = await repository.chain_for(session, scan.id)
    if not entries:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="this scan has no evidence chain; it was refused at the gate or never evaluated",
        )
    review = await repository.finalising_review(session, scan.id)
    try:
        rendered, media = service.report_bytes(scan, entries, review, format)
    except UnconfirmedVerdictExportError as refused:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(refused)) from None
    repository.stage_entry(
        session,
        scan.id,
        service.export_entry(entries, fmt=format, rendered=rendered, officer_id=principal.subject),
    )
    await session.commit()
    return Response(content=rendered, media_type=media, status_code=status.HTTP_201_CREATED)
