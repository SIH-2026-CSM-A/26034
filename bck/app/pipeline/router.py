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

import asyncio
import logging
from collections.abc import Callable
from dataclasses import asdict
from datetime import UTC, datetime
from functools import partial
from pathlib import PurePosixPath
from typing import Annotated
from uuid import UUID

import cv2
import numpy as np
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts import CatalogueRecord
from app.core import (
    CalibrationMethod,
    Jurisdiction,
    Principal,
    RoleTier,
    Scan,
    ScanSourceType,
    VendorPrincipal,
    VendorRow,
    get_current_principal,
    get_current_vendor,
    get_session,
    get_session_factory,
    get_settings,
    limit_consumer_scans,
    require_tier,
)
from app.modules.evidence import LocalStorageClient
from app.modules.evidence.storage import AssetPurgedError
from app.modules.measurement import PackageShape
from app.modules.rules import ProductCategory
from app.modules.vendor import RoutingDecision, route_verdict
from app.modules.vendor import repository as vendor_repository
from app.pipeline import repository
from app.pipeline.capture import QualityRejection
from app.pipeline.orchestrator import (
    ARTWORK_RASTER_DPI,
    NOTHING_CONFIRMED,
    ArtworkRefusal,
    Calibration,
    ImageScanResult,
    PackageConfirmations,
    run_artwork_scan,
    run_catalogue_scan,
    run_image_scan,
)
from app.pipeline.responses import scan_detail, scan_summary, stored_detail
from app.pipeline.schemas import (
    CaptureOutcome,
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
        ward=body.ward,
    )
    scan.capture_metadata = {
        CATALOGUE_RECORD_KEY: body.record.model_dump(mode="json"),
        INSTITUTIONAL_KEY: body.institutional_or_industrial_confirmed,
    }
    return await _evaluate_catalogue_scan(
        session,
        scan,
        body.record,
        body.product_category,
        body.institutional_or_industrial_confirmed,
    )


async def _evaluate_catalogue_scan(
    session: AsyncSession,
    scan: Scan,
    record: CatalogueRecord,
    product_category: ProductCategory | None,
    institutional_or_industrial_confirmed: bool,
) -> ScanDetail:
    """Store the scan, evaluate the listing, and write the verdict. Shared with re-evaluation."""
    async with session.begin():
        repository.add_scan(session, scan)

    try:
        verdict = run_catalogue_scan(
            record,
            product_category=product_category,
            evaluated_at=datetime.now(UTC),
            subject_ref=str(scan.id),
            institutional_or_industrial_confirmed=institutional_or_industrial_confirmed,
        )
    except Exception:
        await repository.mark_failed(session, scan)
        logger.exception("catalogue scan %s failed during evaluation", scan.id)
        raise _evaluation_failed(scan.id) from None

    await repository.persist_verdict(session, scan, verdict)
    return scan_detail(scan, verdict, finalised=False)


@scan_router.post("/image", status_code=status.HTTP_201_CREATED)
async def submit_image_scan(
    session: Session,
    principal: Officer,
    background: BackgroundTasks,
    image: Annotated[UploadFile, File()],
    calibration_method: Annotated[CalibrationMethod, Form()] = CalibrationMethod.NONE,
    reference_type: Annotated[str | None, Form()] = None,
    artwork_dpi: Annotated[float | None, Form()] = None,
    product_category: Annotated[ProductCategory | None, Form()] = None,
    institutional_or_industrial_confirmed: Annotated[bool, Form()] = False,
    ward: Annotated[str | None, Form()] = None,
    package_shape: Annotated[PackageShape, Form()] = PackageShape.RECTANGULAR,
    declarations_required_under_other_law: Annotated[bool, Form()] = False,
    rule_33_relaxation_granted: Annotated[bool, Form()] = False,
) -> ScanDetail:
    """Accept a photographed package and evaluate it after this response has gone.

    The last three fields are :class:`PackageConfirmations` — what the officer has
    established about the package that no photograph can: which limb of Rule 7(4) sizes
    the panel, whether Rule 7(5) disapplies Rule 7's sizing, whether a Rule 33 relaxation
    has been recorded. Each defaults to confirming nothing.

    The response is the scan at PROCESSING with no verdict: the row a client polls
    ``GET /scans/{id}`` against until the status moves. Evaluation is not awaited here
    because it is an OCR run of the better part of a minute on CPU, and a request that
    sits silent for that long does not survive a phone on a mobile network — the carrier
    path drops it around twenty-five seconds in, the browser reports "failed to fetch",
    and the verdict that was written a moment later is never seen.

    What evaluation reports is stored, not returned: a verdict and its findings in their
    tables, and the capture instruction, category proposal and display category as the
    scan's :class:`~app.pipeline.schemas.CaptureOutcome`. A rejected capture is not an
    error: the scan returns to RECEIVED with the instruction attached, which is exactly
    what happened — accepted, and no evaluation made of the package.
    """
    return await _accept_image_scan(
        session,
        principal,
        background,
        await image.read(),
        calibration_method=calibration_method,
        reference_type=reference_type,
        artwork_dpi=artwork_dpi,
        product_category=product_category,
        institutional_or_industrial_confirmed=institutional_or_industrial_confirmed,
        ward=ward,
        hold_capture=True,
        confirmations=PackageConfirmations(
            shape=package_shape,
            declarations_required_under_other_law=declarations_required_under_other_law,
            rule_33_relaxation_granted=rule_33_relaxation_granted,
        ),
    )


ARTWORK_TYPES = ("pdf", "svg")
"""What :func:`~app.pipeline.orchestrator.run_artwork_scan` parses, by file extension."""


@scan_router.post("/artwork", status_code=status.HTTP_201_CREATED)
async def submit_artwork_scan(
    session: Session,
    principal: Officer,
    background: BackgroundTasks,
    artwork: Annotated[UploadFile, File()],
    product_category: Annotated[ProductCategory | None, Form()] = None,
    institutional_or_industrial_confirmed: Annotated[bool, Form()] = False,
    ward: Annotated[str | None, Form()] = None,
    package_shape: Annotated[PackageShape, Form()] = PackageShape.RECTANGULAR,
    declarations_required_under_other_law: Annotated[bool, Form()] = False,
    rule_33_relaxation_granted: Annotated[bool, Form()] = False,
) -> ScanDetail:
    """Accept pre-print artwork of the principal display panel — a PDF or an SVG.

    The one path on which a millimetre is exact: the file states its own physical size, so
    every measurement is :class:`~app.contracts.MeasurementExact` and no calibration is
    asked for. Same shape as the image route otherwise — the scan is returned at
    PROCESSING and polled, because the render is still read by OCR.

    Stored with :attr:`~app.core.CalibrationMethod.ARTWORK`, which is the typed field that
    already means "physical sizes are known exactly", and the file type beside it in
    ``capture_metadata``. The file is held so a category confirmation can evaluate it
    again, exactly as a photograph is.
    """
    kind = PurePosixPath(artwork.filename or "").suffix.lstrip(".").lower()
    if kind not in ARTWORK_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"artwork must be one of {', '.join(ARTWORK_TYPES)}, by file extension",
        )
    return await _accept_artwork_scan(
        session,
        principal,
        background,
        await artwork.read(),
        kind,
        product_category=product_category,
        institutional_or_industrial_confirmed=institutional_or_industrial_confirmed,
        ward=ward,
        confirmations=PackageConfirmations(
            shape=package_shape,
            declarations_required_under_other_law=declarations_required_under_other_law,
            rule_33_relaxation_granted=rule_33_relaxation_granted,
        ),
    )


async def _accept_artwork_scan(
    session: AsyncSession,
    principal: Principal,
    background: BackgroundTasks,
    file_bytes: bytes,
    kind: str,
    *,
    product_category: ProductCategory | None,
    institutional_or_industrial_confirmed: bool,
    ward: str | None,
    confirmations: PackageConfirmations,
    re_evaluation_of: UUID | None = None,
) -> ScanDetail:
    """Store the artwork scan at PROCESSING, queue its evaluation, and return the row."""
    scan = repository.new_scan(
        principal,
        ScanSourceType.PHYSICAL_LABEL,
        CalibrationMethod.ARTWORK,
        product_category,
        ward=ward,
    )
    scan.image_refs = _hold_capture(file_bytes)
    scan.capture_metadata = {
        ARTWORK_TYPE_KEY: kind,
        "artwork_dpi": ARTWORK_RASTER_DPI,
        INSTITUTIONAL_KEY: institutional_or_industrial_confirmed,
        CONFIRMATIONS_KEY: asdict(confirmations),
    }
    if re_evaluation_of is not None:
        scan.capture_metadata[RE_EVALUATION_KEY] = str(re_evaluation_of)
    async with session.begin():
        repository.add_scan(session, scan)
    await repository.mark_processing(session, scan)

    background.add_task(
        _evaluate_in_background,
        scan.id,
        partial(
            run_artwork_scan,
            file_bytes,
            kind,
            product_category=product_category,
            evaluated_at=datetime.now(UTC),
            subject_ref=str(scan.id),
            institutional_or_industrial_confirmed=institutional_or_industrial_confirmed,
            confirmations=confirmations,
        ),
    )
    return scan_detail(scan, None, finalised=False)


async def _accept_image_scan(
    session: AsyncSession,
    principal: Principal,
    background: BackgroundTasks,
    image_bytes: bytes,
    *,
    calibration_method: CalibrationMethod,
    reference_type: str | None,
    artwork_dpi: float | None,
    product_category: ProductCategory | None,
    institutional_or_industrial_confirmed: bool,
    ward: str | None = None,
    hold_capture: bool = False,
    re_evaluation_of: UUID | None = None,
    confirmations: PackageConfirmations = NOTHING_CONFIRMED,
) -> ScanDetail:
    """Store the scan at PROCESSING, queue evaluation, and return the row to poll.

    ``hold_capture`` keeps the uploaded bytes so the scan can be evaluated again once its
    category is confirmed. It is the officer routes' to set; the consumer route never does.
    """
    calibration = ImageCalibration(
        method=calibration_method, reference_type=reference_type, artwork_dpi=artwork_dpi
    )
    frame = _decode(image_bytes)
    scan = repository.new_scan(
        principal,
        ScanSourceType.PHYSICAL_LABEL,
        calibration.method,
        product_category,
        ward=ward,
    )
    if hold_capture:
        scan.image_refs = _hold_capture(image_bytes)
    scan.capture_metadata = {
        "reference_type": calibration.reference_type,
        "artwork_dpi": calibration.artwork_dpi,
        INSTITUTIONAL_KEY: institutional_or_industrial_confirmed,
        CONFIRMATIONS_KEY: asdict(confirmations),
    }
    if re_evaluation_of is not None:
        scan.capture_metadata[RE_EVALUATION_KEY] = str(re_evaluation_of)
    async with session.begin():
        repository.add_scan(session, scan)
    await repository.mark_processing(session, scan)

    background.add_task(
        _evaluate_in_background,
        scan.id,
        partial(
            run_image_scan,
            frame,
            calibration=Calibration(
                method=calibration.method,
                reference_type=calibration.reference_type,
                artwork_dpi=calibration.artwork_dpi,
            ),
            product_category=product_category,
            evaluated_at=datetime.now(UTC),
            subject_ref=str(scan.id),
            institutional_or_industrial_confirmed=institutional_or_industrial_confirmed,
            confirmations=confirmations,
        ),
    )
    return scan_detail(scan, None, finalised=False)


# ponytail: one evaluation at a time, on a thread. The VM has four cores and PaddleOCR
# takes all of them for one image; two at once would each take twice as long. Paddle
# also holds the interpreter lock inside its inference call — measured at up to 21 s on
# the VM — so the loop, and every poll for this scan, stalls for that long. Tolerated by
# the client, which retries a failed read. The upgrade is a one-worker process pool,
# which frees the loop entirely; it is not done here because the route tests patch the
# pipeline in-process, and a spawned worker would not see the patches.
_EVALUATION_LOCK = asyncio.Lock()


async def _evaluate_in_background(
    scan_id: UUID,
    evaluate: Callable[[], QualityRejection | ArtworkRefusal | ImageScanResult],
) -> None:
    """Run the pipeline off the event loop and store what it says.

    ``evaluate`` is the whole call, bound at submission — :func:`run_image_scan` for a
    photograph, :func:`run_artwork_scan` for artwork — so the two paths share every line
    that stores an outcome and differ only in what they hand the chain.

    Runs after the submission response has been sent, on a session of its own — the
    request's session is closed by then. The pipeline is synchronous CPU work, so it goes
    to a thread; while it runs the loop stays free to answer the polls for this very scan.
    Every exit writes a status: nothing leaves a scan at PROCESSING forever.
    """
    async with get_session_factory()() as session:
        # Loaded in a transaction of its own and released: the helpers below each open
        # theirs, and a load left autobegun would make the first of them raise.
        async with session.begin():
            scan = await session.get(Scan, scan_id)
        assert scan is not None  # written and committed by the request that queued this
        try:
            async with _EVALUATION_LOCK:
                outcome = await asyncio.to_thread(evaluate)
        except Exception:
            await repository.mark_failed(session, scan)
            logger.exception("scan %s failed during evaluation", scan.id)
            return

        if isinstance(outcome, QualityRejection):
            await repository.persist_quality_rejection(session, scan, outcome)
            return
        if isinstance(outcome, ArtworkRefusal):
            await repository.persist_refusal(session, scan, outcome.reason)
            return

        assert isinstance(outcome, ImageScanResult)
        # Every span reaches the evidence record, with the unplaced ones named inside it.
        # `spans` already holds them, so they are identified by id rather than repeated.
        # `product_category` on the row is the officer's own answer, written at submission;
        # the proposal and the display classification are stored beside it, never in it.
        await repository.persist_verdict(
            session,
            scan,
            outcome.verdict,
            outcome.spans,
            [span.span_id for span in outcome.unclassified_spans],
            outcome=CaptureOutcome(
                category_proposal=outcome.category_proposal,
                display_category=outcome.display_category,
            ),
        )


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

    return await _stored(session, scan)


async def _stored(session: AsyncSession, scan: Scan) -> ScanDetail:
    verdict = await repository.latest_verdict(session, scan.id)
    findings = () if verdict is None else await repository.findings_for(session, verdict.id)
    return stored_detail(
        scan,
        verdict=verdict,
        findings=findings,
        finalised=await repository.is_finalised(session, scan.id),
        panel_spans=await repository.panel_spans_for(session, scan.id),
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


# --- Category confirmation --------------------------------------------------------------
#
# The category proposal only exists once a scan has been evaluated, so an officer can only
# confirm a category after the fact — and a confirmed category is a precondition of rule
# evaluation, not a label applied after it. So confirming evaluates the same capture again
# under the confirmed category, as a NEW scan. The original row is never edited: its
# ``product_category`` stays what it was evaluated under, which is none, and its verdict
# stays the verdict of that evaluation. ``new_scan`` remains the only place a
# ``Scan.product_category`` is ever written, and it is handed the officer's typed answer.

CATALOGUE_RECORD_KEY = "catalogue_record"
INSTITUTIONAL_KEY = "institutional_or_industrial_confirmed"
RE_EVALUATION_KEY = "re_evaluation_of"
ARTWORK_TYPE_KEY = "artwork_file_type"
CONFIRMATIONS_KEY = "confirmations"
STORAGE_KEY = "storage_key"
"""Keys this router writes into ``Scan.capture_metadata`` and ``Scan.image_refs``."""


class CategoryConfirmation(BaseModel):
    """An officer's answer to "which product category is this package".

    One required field and nothing else is accepted. There is no ``accept_proposal`` flag
    and no default: the category has to be stated in the request by the officer making it,
    so there is no spelling of this body that means "whatever the pipeline read".
    """

    model_config = ConfigDict(extra="forbid")

    product_category: ProductCategory


def _hold_capture(image_bytes: bytes) -> list[dict[str, str]]:
    """Keep the uploaded bytes, content-addressed, and return the scan's ``image_refs``."""
    directory = get_settings().capture_store_dir
    if directory is None:
        return []
    return [{STORAGE_KEY: LocalStorageClient(str(directory)).store_image(image_bytes)}]


def _held_capture(scan: Scan) -> bytes:
    """The bytes behind an image scan, or a 409 where they are not held."""
    directory = get_settings().capture_store_dir
    try:
        if directory is None or not scan.image_refs:
            raise FileNotFoundError
        return LocalStorageClient(str(directory)).get_image(scan.image_refs[0][STORAGE_KEY])
    except (FileNotFoundError, AssetPurgedError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "the capture behind this scan is not held, so it cannot be evaluated again; "
                "photograph the package again and state the category when submitting"
            ),
        ) from None


def _as_filed(subject: str, territory: Scan | VendorRow) -> Principal:
    """``subject``, filing over the territory a stored row records.

    A :class:`Principal` only because ``new_scan`` files by one; the tier is the depth the
    row records. For a re-evaluation the row is the original scan — a controller confirming
    a district scan must not lift it out of that district's view. For a vendor scan it is
    the premises on the register. Both were written from a verified token or by an officer,
    and neither is the request.
    """
    jurisdiction = Jurisdiction(
        state=territory.state, region=territory.region, district=territory.district
    )
    tier = (
        RoleTier.DISTRICT
        if territory.district
        else RoleTier.REGIONAL
        if territory.region
        else RoleTier.STATE
    )
    return Principal(subject=subject, tier=tier, jurisdiction=jurisdiction)


@scan_router.post("/{scan_id}/category", status_code=status.HTTP_201_CREATED)
async def confirm_category(
    scan_id: UUID,
    body: CategoryConfirmation,
    session: Session,
    background: BackgroundTasks,
    principal: Annotated[Principal, Depends(require_tier(RoleTier.DISTRICT))],
) -> ScanDetail:
    """Confirm a scan's product category, and evaluate its capture again under it.

    Returns a **new** scan carrying the confirmed category — for a photograph, at
    PROCESSING, to be polled like any submission. The original is left exactly as it was.
    An officer act: it sits behind the officer principal, and nothing the pipeline read —
    no proposal, no display classification — is consulted here or can stand in for the
    body's ``product_category``.
    """
    async with session.begin():
        original = await repository.get_scan(session, scan_id, principal)
        if original is None:
            raise _not_found()
    filed_as = _as_filed(principal.subject, original)
    institutional = bool(original.capture_metadata.get(INSTITUTIONAL_KEY, False))
    confirmations = _confirmations_of(original)

    if original.source_type is ScanSourceType.CATALOGUE_RECORD:
        stored = original.capture_metadata.get(CATALOGUE_RECORD_KEY)
        if stored is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="the listing behind this scan is not held; submit it again",
            )
        scan = repository.new_scan(
            filed_as,
            ScanSourceType.CATALOGUE_RECORD,
            CalibrationMethod.NONE,
            body.product_category,
            ward=original.ward,
        )
        scan.capture_metadata = {**original.capture_metadata, RE_EVALUATION_KEY: str(scan_id)}
        return await _evaluate_catalogue_scan(
            session,
            scan,
            CatalogueRecord.model_validate(stored),
            body.product_category,
            institutional,
        )

    if ARTWORK_TYPE_KEY in original.capture_metadata:
        detail = await _accept_artwork_scan(
            session,
            filed_as,
            background,
            _held_capture(original),
            original.capture_metadata[ARTWORK_TYPE_KEY],
            product_category=body.product_category,
            institutional_or_industrial_confirmed=institutional,
            ward=original.ward,
            confirmations=confirmations,
            re_evaluation_of=scan_id,
        )
    else:
        detail = await _accept_image_scan(
            session,
            filed_as,
            background,
            _held_capture(original),
            calibration_method=original.calibration_method,
            reference_type=original.capture_metadata.get("reference_type"),
            artwork_dpi=original.capture_metadata.get("artwork_dpi"),
            product_category=body.product_category,
            institutional_or_industrial_confirmed=institutional,
            ward=original.ward,
            hold_capture=True,
            re_evaluation_of=scan_id,
            confirmations=confirmations,
        )
    # A vendor's scan stays the vendor's when it is evaluated again: the attribution is
    # copied so the re-evaluation is theirs to read back as well as the officer's.
    async with session.begin():
        attribution = await vendor_repository.get_vendor_scan(session, scan_id)
        if attribution is not None:
            vendor_repository.attribute_scan(session, detail.id, attribution.vendor_id)
    return detail


def _confirmations_of(scan: Scan) -> PackageConfirmations:
    """The confirmations a scan was submitted with, so a re-evaluation keeps them."""
    stored = scan.capture_metadata.get(CONFIRMATIONS_KEY)
    if not stored:
        return NOTHING_CONFIRMED
    return PackageConfirmations(
        shape=PackageShape(stored["shape"]),
        declarations_required_under_other_law=bool(stored["declarations_required_under_other_law"]),
        rule_33_relaxation_granted=bool(stored["rule_33_relaxation_granted"]),
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


# --- The consumer surface -------------------------------------------------------------
#
# A member of the public photographs a label and reads back what the rules say about it.
# No login and no identity: every consumer scan is submitted as one fixed principal whose
# jurisdiction is the literal state "consumer". That is not a territory any officer holds,
# so the repository's jurisdiction predicate keeps consumer scans out of every officer
# view and officer scans out of the consumer read route, with no second code path.
#
# The route is unauthenticated and each accepted upload is an OCR run of the better part of
# a minute, so it is limited three ways: per client and overall per minute
# (:func:`app.core.limit_consumer_scans`), and by how many consumer evaluations may be
# queued at once, because every queued scan holds a decoded frame in memory.

CONSUMER = Principal(
    subject="consumer", tier=RoleTier.STATE, jurisdiction=Jurisdiction(state="consumer")
)

consumer_router = APIRouter(prefix="/consumer", tags=["consumer"])

_consumer_pending = 0
"""Consumer evaluations queued or running. Touched only on the event loop, so a plain int."""


def _reserve_consumer_slot() -> None:
    """Take one place in the consumer queue, or a 429 when it is full."""
    global _consumer_pending
    if _consumer_pending >= get_settings().consumer_scans_max_pending:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="the scan queue is full; try again shortly",
            headers={"Retry-After": "60"},
        )
    _consumer_pending += 1


async def _release_consumer_slot() -> None:
    """Give the place back. Queued after the evaluation, so it runs once that has ended."""
    global _consumer_pending
    _consumer_pending -= 1


@consumer_router.post(
    "/scans/image",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(limit_consumer_scans)],
)
async def submit_consumer_image_scan(
    session: Session,
    background: BackgroundTasks,
    image: Annotated[UploadFile, File()],
) -> ScanDetail:
    """Accept a consumer's photograph of a label; poll ``GET /consumer/scans/{id}``.

    Uncalibrated and uncategorised by construction: a consumer confirms no product
    category and places no reference object, so the packaged rules apply unchanged and
    no physical measurement is ever reported from their photograph.
    """
    _reserve_consumer_slot()
    try:
        detail = await _accept_image_scan(
            session,
            CONSUMER,
            background,
            await image.read(),
            calibration_method=CalibrationMethod.NONE,
            reference_type=None,
            artwork_dpi=None,
            product_category=None,
            institutional_or_industrial_confirmed=False,
        )
    except BaseException:
        await _release_consumer_slot()
        raise
    background.add_task(_release_consumer_slot)
    return detail


@consumer_router.get("/scans/{scan_id}")
async def get_consumer_scan(scan_id: UUID, session: Session) -> ScanDetail:
    """One consumer scan in full. An officer's scan is a 404 here, by jurisdiction."""
    scan = await repository.get_scan(session, scan_id, CONSUMER)
    if scan is None:
        raise _not_found()
    return await _stored(session, scan)


# --- The vendor surface ----------------------------------------------------------------
#
# A registered vendor photographs their own stock and reads back what the rules say. The
# scan is an ordinary scan: same quality gate, same rules, same verdict, and **filed in the
# premises' territory**, read from the register — never from the request — so the district
# inspector covering that shop sees it in ``GET /scans`` through the same jurisdiction
# predicate as everything else. That predicate is the routing. What a vendor sees back is
# their own submissions and nothing else, through ``vendor.repository.own_scans``.
#
# A vendor holds a VendorPrincipal, which no officer route accepts, so a vendor cannot
# review, confirm a category, or read another premises' scans, structurally rather than by
# a check in each route.

vendor_scan_router = APIRouter(prefix="/vendor/scans", tags=["vendor"])

Vendor = Annotated[VendorPrincipal, Depends(get_current_vendor)]


class VendorScanView(BaseModel):
    """A vendor's own scan, with where it was routed.

    ``routing`` says which tier's queue the outcome reached and whether it calls for a
    visit; it is ``None`` until the scan has a verdict. The verdict itself is unchanged —
    a vendor reads the same recommendation the officer does.
    """

    model_config = ConfigDict(extra="forbid")

    scan: ScanDetail
    routing: RoutingDecision | None


VENDOR_SUBJECT_PREFIX = "vendor:"
"""On ``Scan.officer_id`` for a vendor-filed scan, so no vendor login can read as an
officer's username."""


async def _premises_of(session: AsyncSession, vendor: VendorPrincipal) -> VendorRow:
    async with session.begin():
        premises = await vendor_repository.get_vendor(session, vendor.vendor_id)
    if premises is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="this vendor is not on the register"
        )
    return premises


@vendor_scan_router.post("/image", status_code=status.HTTP_201_CREATED)
async def submit_vendor_image_scan(
    session: Session,
    vendor: Vendor,
    background: BackgroundTasks,
    image: Annotated[UploadFile, File()],
) -> VendorScanView:
    """A vendor photographs a package on their own shelf; poll ``GET /vendor/scans/{id}``.

    No category and no calibration: a vendor confirms nothing. The officer covering the
    premises confirms the category on the scan the vendor filed, as on any other.
    """
    premises = await _premises_of(session, vendor)
    detail = await _accept_image_scan(
        session,
        _as_filed(f"{VENDOR_SUBJECT_PREFIX}{vendor.subject}", premises),
        background,
        await image.read(),
        calibration_method=CalibrationMethod.NONE,
        reference_type=None,
        artwork_dpi=None,
        product_category=None,
        institutional_or_industrial_confirmed=False,
        hold_capture=True,
    )
    async with session.begin():
        vendor_repository.attribute_scan(session, detail.id, vendor.vendor_id)
    return VendorScanView(scan=detail, routing=None)


@vendor_scan_router.get("")
async def list_vendor_scans(session: Session, vendor: Vendor) -> list[ScanSummary]:
    """This vendor's own submissions, newest first, and nobody else's."""
    scans = await vendor_repository.list_own_scans(session, vendor)
    return [
        scan_summary(
            scan,
            verdict=await repository.latest_verdict(session, scan.id),
            finalised=await repository.is_finalised(session, scan.id),
        )
        for scan in scans
    ]


@vendor_scan_router.get("/{scan_id}")
async def get_vendor_scan(scan_id: UUID, session: Session, vendor: Vendor) -> VendorScanView:
    """One of this vendor's scans. Another vendor's, or an officer's, is a 404."""
    scan = await vendor_repository.get_own_scan(session, scan_id, vendor)
    if scan is None:
        raise _not_found()
    detail = await _stored(session, scan)
    routing = None
    if detail.verdict is not None:
        routing = route_verdict(
            Jurisdiction(state=scan.state, region=scan.region, district=scan.district),
            detail.verdict,
        )
    return VendorScanView(scan=detail, routing=routing)
