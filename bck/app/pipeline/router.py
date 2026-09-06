"""The scan endpoints, and the transaction boundaries they own.

Thin: parse in, delegate, return out. The logic lives in the orchestrator and the findings
modules; every query lives in the repository.
**Where the transaction sits.** :func:`~app.core.db.get_session` yields a session and does
not commit: a teardown-commit fires after the response body is built, where a failure can
no longer change the status code the client already has. So each handler opens its own
``session.begin()``, and a submission opens two — the scan is inserted and committed before
any vision runs, the pipeline then runs with **no transaction open** (PaddleOCR and YOLO
would otherwise hold a pool connection for seconds), and the verdict and its findings are
written together in one atomic block.

A crash between the two leaves a scan at RECEIVED, which is exactly true: accepted and
stored, evaluation unfinished. A stage that raises marks the scan FAILED in its own
transaction and writes no verdict — a partial finding set would read as "we looked and
found less wrong than we did".

**Authorisation is here, not in the interface.** Every read goes through the repository,
which scopes it to the caller's jurisdiction. A scan outside it is a 404 — the same answer
as one that does not exist, because a 403 would tell an officer in one state that a package
is under examination in another. 403 is kept for the case it is for: an officer inside the
jurisdiction whose tier is too low for the action.
"""

import logging
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import (
    CalibrationMethod,
    Principal,
    RoleTier,
    ScanSourceType,
    get_current_principal,
    get_session,
    require_tier,
)
from app.modules.rules import ProductCategory
from app.pipeline import repository
from app.pipeline.capture import QualityRejection
from app.pipeline.orchestrator import (
    Calibration,
    ImageScanResult,
    run_catalogue_scan,
    run_image_scan,
)
from app.pipeline.responses import scan_detail, scan_summary, stored_detail
from app.pipeline.schemas import (
    CatalogueScanRequest,
    ImageCalibration,
    ReviewRequest,
    ReviewResponse,
    ScanDetail,
    ScanFilters,
    ScanSummary,
)

logger = logging.getLogger(__name__)

scan_router = APIRouter(prefix="/scans", tags=["scans"])

Session = Annotated[AsyncSession, Depends(get_session)]
Officer = Annotated[Principal, Depends(get_current_principal)]


@scan_router.post("", status_code=status.HTTP_201_CREATED)
async def submit_catalogue_scan(
    body: CatalogueScanRequest, session: Session, principal: Officer
) -> ScanDetail:
    """Evaluate a structured listing. The non-image ingestion path, in its own right."""
    scan = repository.new_scan(
        principal,
        ScanSourceType.CATALOGUE_RECORD,
        CalibrationMethod.NONE,
        body.product_category,
    )
    async with session.begin():
        repository.add_scan(session, scan)

    try:
        record = run_catalogue_scan(
            body.record,
            product_category=body.product_category,
            evaluated_at=datetime.now(UTC),
            subject_ref=str(scan.id),
        )
    except Exception:
        await repository.mark_failed(session, scan)
        logger.exception("catalogue scan %s failed during evaluation", scan.id)
        raise _evaluation_failed(scan.id) from None

    await repository.persist_verdict(session, scan, record)
    return scan_detail(scan, record, finalised=False)


@scan_router.post("/image", status_code=status.HTTP_201_CREATED)
async def submit_image_scan(
    session: Session,
    principal: Officer,
    image: Annotated[UploadFile, File()],
    calibration_method: Annotated[CalibrationMethod, Form()] = CalibrationMethod.NONE,
    reference_type: Annotated[str | None, Form()] = None,
    artwork_dpi: Annotated[float | None, Form()] = None,
    product_category: Annotated[ProductCategory | None, Form()] = None,
) -> ScanDetail:
    """Evaluate a photographed package, or return a capture instruction.

    A rejected capture is a 201 with no verdict, not an error: the submission was accepted
    and stored, and what came back is an instruction rather than a finding. The scan stays
    at RECEIVED, whose meaning is exactly that — accepted, evaluation not started.
    """
    calibration = ImageCalibration(
        method=calibration_method, reference_type=reference_type, artwork_dpi=artwork_dpi
    )
    frame = _decode(await image.read())
    scan = repository.new_scan(
        principal, ScanSourceType.PHYSICAL_LABEL, calibration.method, product_category
    )
    async with session.begin():
        repository.add_scan(session, scan)

    try:
        outcome = run_image_scan(
            frame,
            calibration=Calibration(
                method=calibration.method,
                reference_type=calibration.reference_type,
                artwork_dpi=calibration.artwork_dpi,
            ),
            product_category=product_category,
            evaluated_at=datetime.now(UTC),
            subject_ref=str(scan.id),
        )
    except Exception:
        await repository.mark_failed(session, scan)
        logger.exception("image scan %s failed during evaluation", scan.id)
        raise _evaluation_failed(scan.id) from None

    if isinstance(outcome, QualityRejection):
        return scan_detail(scan, None, finalised=False, quality=outcome)

    assert isinstance(outcome, ImageScanResult)
    await repository.persist_verdict(session, scan, outcome.verdict)
    return scan_detail(scan, outcome.verdict, finalised=False)


@scan_router.get("")
async def list_scans(
    session: Session, principal: Officer, filters: Annotated[ScanFilters, Depends()]
) -> list[ScanSummary]:
    """Scans this officer may see, narrowed by the supplied filters and by nothing else.

    The jurisdiction predicate is applied by the repository on every query and is not
    something a caller can widen — there is no jurisdiction parameter on this route.
    """
    scans = await repository.list_scans(session, principal, filters)
    return [
        scan_summary(
            scan,
            verdict=await repository.latest_verdict(session, scan.id),
            finalised=await repository.is_finalised(session, scan.id),
        )
        for scan in scans
    ]


@scan_router.get("/{scan_id}")
async def get_scan(scan_id: UUID, session: Session, principal: Officer) -> ScanDetail:
    """One scan in full.

    404 both for a scan that does not exist and for one outside this officer's
    jurisdiction. That is not laziness about the difference: a 403 would confirm to an
    officer in one state that a package is under examination in another, which is
    enforcement activity they have no right to know of.
    """
    scan = await repository.get_scan(session, scan_id, principal)
    if scan is None:
        raise _not_found()

    verdict = await repository.latest_verdict(session, scan.id)
    findings = () if verdict is None else await repository.findings_for(session, verdict.id)
    return stored_detail(
        scan,
        verdict=verdict,
        findings=findings,
        finalised=await repository.is_finalised(session, scan.id),
    )


@scan_router.post("/{scan_id}/review", status_code=status.HTTP_201_CREATED)
async def review_scan(
    scan_id: UUID,
    body: ReviewRequest,
    session: Session,
    principal: Annotated[Principal, Depends(require_tier(RoleTier.DISTRICT))],
) -> ReviewResponse:
    """Record an officer's action on a verdict. **The only way a scan is ever finalised.**

    Nothing else in the application constructs a review, so there is no automated path to
    a finalised scan — not a background job, not a re-evaluation, not the submit route.
    Confirming, rejecting or overriding is something a person does, and this is where they
    do it.
    """
    # One transaction for the read and the write, not two. The reads themselves begin a
    # transaction implicitly, so opening another afterwards raises; and the officer's
    # decision should be recorded against the verdict that was read for it, not against
    # whatever a second transaction would find.
    async with session.begin():
        scan = await repository.get_scan(session, scan_id, principal)
        if scan is None:
            raise _not_found()

        verdict = await repository.latest_verdict(session, scan.id)
        if verdict is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="this scan has no verdict to review",
            )

        row = repository.record_review(
            session,
            scan_id=scan.id,
            verdict_id=verdict.id,
            officer_id=principal.subject,
            review=body,
        )
        await session.flush()
        finalised = await repository.is_finalised(session, scan.id)

    return ReviewResponse(
        id=row.id,
        scan_id=row.scan_id,
        verdict_id=row.verdict_id,
        action=row.action,
        officer_id=row.officer_id,
        note=row.note,
        overridden_verdict=row.overridden_verdict,
        supersedes_id=row.supersedes_id,
        created_at=row.created_at,
        rule_set_version=verdict.rule_set_version,
        finalised=finalised,
    )


def _decode(payload: bytes) -> np.ndarray:
    """The uploaded bytes as an image, or a 422 naming the problem.

    Decoding here rather than in the orchestrator keeps the chain taking an image and this
    route taking a request. An undecodable upload is a malformed request, not a scan that
    failed the quality gate, and the two must not return the same thing: one means send a
    different file, the other means photograph the package again.
    """
    frame = cv2.imdecode(np.frombuffer(payload, dtype=np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="the uploaded file could not be decoded as an image",
        )
    return frame


def _not_found() -> HTTPException:
    """The single answer for absent and out-of-jurisdiction alike."""
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="scan not found")


def _evaluation_failed(scan_id: UUID) -> HTTPException:
    """A 500 carrying the scan id as a correlation handle and nothing else.

    The stack trace, the stage and the exception go to the log. What the client gets is an
    identifier they can quote, which is what lets an operator find the detail without the
    detail being served to whoever asked.
    """
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"evaluation did not complete for scan {scan_id}; the scan is recorded as failed",
    )
