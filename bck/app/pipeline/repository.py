"""Every database query the scan path makes, and the only place a review is written.

Two guarantees live here rather than in the routes above.

**Every read is scoped.** :func:`~app.core.rbac.scope_to_jurisdiction` constrains the
statement it is handed and nothing else, so a query that never passes through it is not
scoped and no permission check elsewhere will notice. Putting all of them in one file is
what makes "is every read scoped?" a question somebody can answer by reading a file rather
than by grepping the whole application. A scan outside the caller's jurisdiction is not
found — the same answer as one that does not exist, because a 403 would disclose that
another state is looking at a package.

**There is no update.** This module offers inserts and selects. A review is an event, and
a correction is a new row naming the one it supersedes, so no code path can edit what an
officer recorded. :func:`record_review` is the only construction of a
:class:`~app.core.models.ReviewRow` in the application, and a structural test asserts that
it stays the only one — that is what makes "nothing is finalised without an officer" a
property of the code rather than a promise about it.
"""

import json
from collections.abc import Sequence
from uuid import UUID, uuid4

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts import DeclarationField, EvidenceAssetType, ExtractedSpan, VerdictRecord
from app.core import (
    CalibrationMethod,
    EvidenceEntryRow,
    FieldFindingRow,
    Principal,
    ReviewAction,
    ReviewRow,
    Scan,
    ScanSourceType,
    ScanStatus,
    VerdictRow,
    scope_to_jurisdiction,
)
from app.modules.evidence import create_genesis_entry
from app.modules.rules import ProductCategory, default_rule_set_version
from app.pipeline.schemas import ReviewRequest, ScanFilters

FINALISING_ACTIONS = frozenset({ReviewAction.CONFIRM, ReviewAction.REJECT, ReviewAction.OVERRIDE})
"""The actions that end a review. ANNOTATE and REQUEST_RECAPTURE are recorded events: a
note is not a decision, and asking for a better photograph is a statement about the
evidence rather than about the package."""


def scoped_scans(principal: Principal) -> Select:
    """A SELECT over the scans this principal may see, and no others."""
    return scope_to_jurisdiction(select(Scan), principal, Scan)


async def get_scan(session: AsyncSession, scan_id: UUID, principal: Principal) -> Scan | None:
    """One scan, or ``None`` where it does not exist *or* is not this officer's to see.

    Deliberately one query and one answer. Distinguishing "absent" from "outside your
    jurisdiction" would tell an officer in one state that a package is under examination
    in another, which is enforcement activity they have no right to know of. The route
    turns this ``None`` into a 404 either way.
    """
    statement = scoped_scans(principal).where(Scan.id == scan_id)
    return (await session.scalars(statement)).one_or_none()


async def list_scans(
    session: AsyncSession, principal: Principal, filters: ScanFilters
) -> Sequence[Scan]:
    """Scans matching ``filters``, always within the caller's jurisdiction.

    ``product`` and ``manufacturer`` need no columns on :class:`~app.core.models.Scan`:
    both are declarations, they live on the findings, and matching them there means the
    filter searches what was actually read off the package rather than a copy of it that
    could disagree.
    """
    statement = scoped_scans(principal)
    if filters.status is not None:
        statement = statement.where(Scan.status == filters.status)
    if filters.created_from is not None:
        statement = statement.where(Scan.created_at >= filters.created_from)
    if filters.created_to is not None:
        statement = statement.where(Scan.created_at <= filters.created_to)
    statement = _by_declaration(statement, DeclarationField.COMMON_OR_GENERIC_NAME, filters.product)
    statement = _by_declaration(statement, DeclarationField.NAME_AND_ADDRESS, filters.manufacturer)
    statement = statement.order_by(Scan.created_at.desc()).limit(filters.limit)
    return (await session.scalars(statement.offset(filters.offset))).all()


def _by_declaration(statement: Select, field: DeclarationField, term: str | None) -> Select:
    """Narrow to scans whose findings read ``term`` for one declaration."""
    if not term:
        return statement
    match = (
        select(VerdictRow.scan_id)
        .join(FieldFindingRow, FieldFindingRow.verdict_id == VerdictRow.id)
        .where(FieldFindingRow.field == field)
        .where(FieldFindingRow.observed_value.ilike(f"%{term}%"))
    )
    return statement.where(Scan.id.in_(match))


async def latest_verdict(session: AsyncSession, scan_id: UUID) -> VerdictRow | None:
    """The most recent verdict for a scan.

    Re-evaluating writes a second row rather than editing the first, so "the verdict" is
    always the latest of several and never the only one.
    """
    statement = (
        select(VerdictRow)
        .where(VerdictRow.scan_id == scan_id)
        .order_by(VerdictRow.evaluated_at.desc())
        .limit(1)
    )
    return (await session.scalars(statement)).one_or_none()


async def findings_for(session: AsyncSession, verdict_id: UUID) -> Sequence[FieldFindingRow]:
    """Every finding behind one verdict, in a stable order."""
    statement = (
        select(FieldFindingRow)
        .where(FieldFindingRow.verdict_id == verdict_id)
        .order_by(FieldFindingRow.rule_id, FieldFindingRow.field)
    )
    return (await session.scalars(statement)).all()


async def is_finalised(session: AsyncSession, scan_id: UUID) -> bool:
    """Whether an officer has confirmed, rejected or overridden this scan's verdict.

    Computed from the review rows every time rather than cached on the scan. A flag can be
    set by whatever holds the row; this can only become true because somebody called
    :func:`record_review`.
    """
    statement = (
        select(func.count())
        .select_from(ReviewRow)
        .where(ReviewRow.scan_id == scan_id)
        .where(ReviewRow.action.in_(FINALISING_ACTIONS))
    )
    return bool((await session.scalars(statement)).one())


def add_scan(session: AsyncSession, scan: Scan) -> Scan:
    """Stage a new scan. The caller owns the transaction and the commit."""
    session.add(scan)
    return scan


async def add_verdict(session: AsyncSession, scan: Scan, record: VerdictRecord) -> VerdictRow:
    """Stage a verdict and every finding behind it, in one unit of work.

    Both or neither. A verdict row with no findings has no evidence chain behind it, and
    :class:`~app.contracts.VerdictRecord` will not construct without at least one finding
    precisely so that this cannot be written.

    **The flush between the two is load-bearing.** SQLAlchemy orders dependent inserts
    from ``relationship()`` declarations, not from raw ``ForeignKey`` columns, and this
    schema deliberately has none — a relationship on an async mapper lazy-loads on
    attribute access and raises ``MissingGreenlet`` while the response is being
    serialised, a long way from the code that caused it. Without relationships the unit of
    work is free to insert the findings first, and Postgres rejects them with a foreign
    key violation naming a verdict that does not exist yet. Flushing the parent makes the
    order explicit instead of relying on one the ORM never promised.
    """
    verdict = VerdictRow(
        # Assigned here, not left to the column default. That default is applied by
        # SQLAlchemy at INSERT, so reading ``verdict.id`` before the flush would hand every
        # finding a null foreign key — and the findings are built in this same block,
        # before anything reaches the database.
        id=uuid4(),
        scan_id=scan.id,
        verdict=record.verdict,
        subject_ref=record.subject_ref,
        rule_set_version=record.rule_set_version,
        evaluated_at=record.evaluated_at,
        field_providers={
            field.value: provider.value for field, provider in record.field_providers.items()
        },
    )
    session.add(verdict)
    await session.flush()
    for found in record.findings:
        session.add(
            FieldFindingRow(
                verdict_id=verdict.id,
                field=found.field,
                # The snapshot stays the record of what was applied; this column is a
                # queryable copy of one of its fields, written from it and nowhere else.
                rule_id=found.rule_snapshot.rule_id,
                state=found.state,
                reason=found.reason,
                observed_value=found.observed_value,
                expected_value=found.expected_value,
                rule_snapshot=found.rule_snapshot.model_dump(mode="json"),
                evidence_span_ids=list(found.evidence_span_ids),
                evidence_regions=[],
            )
        )
    return verdict


def record_review(
    session: AsyncSession,
    *,
    scan_id: UUID,
    verdict_id: UUID,
    officer_id: str,
    review: ReviewRequest,
) -> ReviewRow:
    """Stage one officer action. **The only place a review row is ever constructed.**

    A structural test asserts that, because the guarantee it carries is not about this
    function — it is about every other path in the application not having one. Finalisation
    is the existence of a row with a finalising action, so a second constructor anywhere
    would be a way for something other than an officer to finalise a scan.
    """
    row = ReviewRow(
        scan_id=scan_id,
        verdict_id=verdict_id,
        action=review.action,
        officer_id=officer_id,
        note=review.note,
        overridden_verdict=review.overridden_verdict,
        supersedes_id=review.supersedes_id,
    )
    session.add(row)
    return row


def add_evidence_entry(
    session: AsyncSession,
    scan: Scan,
    record: VerdictRecord,
    spans: Sequence[ExtractedSpan],
    unclassified_span_ids: Sequence[str] = (),
) -> EvidenceEntryRow:
    """Hash-chain the verdict and every span it was read from, and stage the entry.

    The genesis entry for a scan. Re-evaluation appends rather than replacing, which is
    what :func:`~app.modules.evidence.append_entry` is for; there is one verdict per scan
    today so there is one entry.

    **Every span goes into the payload, and which ones went unplaced is recorded with
    them.** Text that was read and bound to nothing is evidence in its own right: it is
    what answers "then what does the label say there?" when a finding reports a declaration
    missing, and leaving it out would make an INSUFFICIENT_EVIDENCE finding unauditable.
    ``spans`` is the whole set and ``unclassified_span_ids`` names the leftovers within it,
    rather than listing them twice. Both are inside the hash for the same reason the
    verdict is: so nobody can add, remove or quietly reclassify one afterwards.

    The payload is hashed and stored as *the same string*. ``compute_payload_hash``
    serialises a dict to canonical JSON, so the canonical form is built once here and
    handed over as text: ``payload_json`` then holds the exact bytes that were hashed, and
    verification cannot report a broken chain nobody touched.
    """
    payload = {
        "verdict": record.model_dump(mode="json"),
        "spans": [span.model_dump(mode="json") for span in spans],
        # Which of those the binder could not place, by id rather than by repeating them.
        # The distinction is the useful part and it belongs inside the hash: an officer
        # reading "this declaration is missing" needs to know which text was read and left
        # over, and nobody should be able to reclassify a span after the fact.
        "unclassified_span_ids": list(unclassified_span_ids),
    }
    payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    timestamp = record.evaluated_at.isoformat()
    entry = create_genesis_entry(payload_json, timestamp, EvidenceAssetType.AUDIT_LOG)

    row = EvidenceEntryRow(
        scan_id=scan.id,
        sequence=entry.sequence,
        timestamp=entry.timestamp,
        payload_hash=entry.payload_hash,
        prev_hash=entry.prev_hash,
        entry_hash=entry.entry_hash,
        payload_json=payload_json,
        asset_type=entry.asset_type,
    )
    session.add(row)
    return row


async def persist_verdict(
    session: AsyncSession,
    scan: Scan,
    record: VerdictRecord,
    spans: Sequence[ExtractedSpan] = (),
    unclassified_span_ids: Sequence[str] = (),
) -> None:
    """Write the verdict, its findings, its evidence entry and the scan's completion.

    One transaction, all of it or none. A verdict without its findings has no evidence
    chain behind it, and a verdict without its evidence entry is one nobody can later show
    was not edited.

    The scan is already persistent in this session from the first transaction, so it is
    mutated rather than merged. A ``merge`` here would emit a SELECT, and that SELECT
    triggers an autoflush part-way through building the unit of work — which is how the
    findings came to be inserted ahead of the verdict they point at.
    """
    async with session.begin():
        await add_verdict(session, scan, record)
        add_evidence_entry(session, scan, record, spans, unclassified_span_ids)
        scan.status = ScanStatus.COMPLETE


async def mark_failed(session: AsyncSession, scan: Scan) -> None:
    """Record that processing did not finish, in a transaction of its own.

    FAILED is distinct from every verdict: a scan that crashed carries no finding about
    the package at all, and saying so is not the same as saying nothing was wrong.
    """
    async with session.begin():
        scan.status = ScanStatus.FAILED


def new_scan(
    principal: Principal,
    source_type: ScanSourceType,
    calibration: CalibrationMethod,
    product_category: ProductCategory | None,
) -> Scan:
    """A scan row from the caller's *verified* jurisdiction, never from a request body."""
    return Scan(
        id=uuid4(),
        source_type=source_type,
        status=ScanStatus.RECEIVED,
        calibration_method=calibration,
        state=principal.jurisdiction.state,
        region=principal.jurisdiction.region,
        district=principal.jurisdiction.district,
        officer_id=principal.subject,
        rule_set_version=default_rule_set_version(),
        product_category=None if product_category is None else product_category.value,
        image_refs=[],
        capture_metadata={},
    )
