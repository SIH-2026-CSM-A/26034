"""The tables the scan path writes.

Only what a scan actually produces: the scan itself, the verdict it reached, the
per-field findings behind that verdict, and the evidence chain entries that make the
whole thing checkable afterwards. No users table — officers are still seeded from
``OFFICERS`` — and no table for a module that has no caller yet.

These are ORM models, not contract types. ``app.contracts`` holds the shapes that cross
a module boundary; this holds the shapes that cross a process restart. The two are
deliberately separate, and the enums that appear in both are imported from ``contracts``
rather than restated, so a state can never mean one thing in memory and another on disk.

The one guarantee to read before editing anything here: **``FieldFindingRow.state`` and
``VerdictRow.verdict`` are NOT NULL with no default of any kind.**
``INSUFFICIENT_EVIDENCE`` says we could not read the declaration; ``FAIL`` says we read
it and it falls short. There is no value the database may supply for either, because any
value it supplied would be one of those two answers invented by storage.

The vocabularies these tables store live in :mod:`app.core.enums` and the column
plumbing in :mod:`app.core.schema`; this file is the schema itself.

The jurisdiction columns and the evidence-chain column types are equally load-bearing and
are explained on the columns themselves. ``core/README.md`` carries all of it in full.
"""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.contracts import DeclarationField, EvidenceAssetType, FieldState, Verdict
from app.core.enums import (
    CalibrationMethod,
    ReviewAction,
    ScanSourceType,
    ScanStatus,
)
from app.core.schema import (
    JURISDICTION_LEVEL_LENGTH,
    SHA256_HEX_LENGTH,
    Base,
    Json,
    enum_column,
)


class Scan(Base):
    """One package or listing submitted for evaluation, and where it came from."""

    __tablename__ = "scans"
    __table_args__ = (Index("ix_scans_state_region_district", "state", "region", "district"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    source_type: Mapped[ScanSourceType] = mapped_column(
        enum_column(ScanSourceType, "scan_source_type"), nullable=False
    )
    status: Mapped[ScanStatus] = mapped_column(
        enum_column(ScanStatus, "scan_status"), nullable=False
    )
    calibration_method: Mapped[CalibrationMethod] = mapped_column(
        enum_column(CalibrationMethod, "calibration_method"), nullable=False
    )

    state: Mapped[str] = mapped_column(String(JURISDICTION_LEVEL_LENGTH), nullable=False)
    region: Mapped[str | None] = mapped_column(String(JURISDICTION_LEVEL_LENGTH))
    district: Mapped[str | None] = mapped_column(String(JURISDICTION_LEVEL_LENGTH))
    """The territory this scan sits in, mirroring :class:`app.core.rbac.Jurisdiction`.
    ``region`` and ``district`` are nullable because a state-tier officer's scan pins
    neither; a narrower officer's equality predicate excludes those rows, which is the
    correct answer."""

    officer_id: Mapped[str] = mapped_column(String(JURISDICTION_LEVEL_LENGTH), nullable=False)
    """The submitting officer's :attr:`app.core.rbac.Principal.subject`. Deliberately not
    a foreign key: officers are configuration until there is a users table."""

    rule_set_version: Mapped[str] = mapped_column(String(64), nullable=False)
    """The published rule set this scan was evaluated under, by value."""

    product_category: Mapped[str | None] = mapped_column(String(64))
    """The officer's *confirmed* product category, or ``None`` where none was confirmed.

    Nullable because the null is the meaningful state: an unconfirmed category routes no
    sector override, so every obligation a sector could carve out is INSUFFICIENT_EVIDENCE
    rather than evaluated against the packaged rules. Confirming a category is an officer
    action, never an inference — routing a package to another Act on a classifier's guess
    would move a real legal obligation on a guess.

    A plain string rather than an enum column because the vocabulary that matters is
    :class:`app.contracts.ProductCategory`. ``core`` may import ``contracts``, so that is
    no longer what stops this being an enum column — what stops it is that changing the
    column type is a migration against a table that already holds these strings, and it
    buys nothing the request boundary does not already do. The value is constrained where
    it enters, in ``pipeline/schemas.py``; a category the sector lookup does not know is
    refused there rather than stored and silently failing to route. Tracked in TODO.md.
    """

    image_refs: Mapped[list[dict[str, Any]]] = mapped_column(Json, nullable=False, default=list)
    """Object-store references for the images behind this scan, one entry each. A scan
    has as many as it has capture angles, and the count varies by source."""

    capture_metadata: Mapped[dict[str, Any]] = mapped_column(Json, nullable=False, default=dict)
    """Everything else known at capture — device, resolution, EXIF, the identity and
    stated dimensions of any reference object. Genuinely shaped differently per source
    and per device, which is what puts it here rather than in columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class VerdictRow(Base):
    """The package-level recommendation reached for one scan.

    Carries **no** reference to a rules table — no ``rule_set_id``, no
    ``rule_definition_id`` — and must never gain one. Every parameter that shaped the
    outcome is snapshotted by value onto :class:`FieldFindingRow`. With nothing to join
    through, a stored verdict cannot be re-adjudicated against rules amended after it was
    issued.

    Append-only. Re-evaluating a scan writes a second row; it does not edit the first.
    """

    __tablename__ = "verdicts"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    scan_id: Mapped[UUID] = mapped_column(ForeignKey("scans.id"), nullable=False, index=True)

    verdict: Mapped[Verdict] = mapped_column(enum_column(Verdict, "verdict"), nullable=False)
    """PASS, REVIEW or POTENTIAL_VIOLATION. Not null and with no default of any kind:
    there is no verdict the database is entitled to invent."""

    subject_ref: Mapped[str] = mapped_column(Text, nullable=False)
    rule_set_version: Mapped[str] = mapped_column(String(64), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    """When the evaluation ran. Rule applicability was resolved against this instant."""

    field_providers: Mapped[dict[str, str]] = mapped_column(Json, nullable=False, default=dict)
    """Declaration field to the provider whose reading was used. Sparse, and nothing
    joins on it."""


class FieldFindingRow(Base):
    """One declaration evaluated against one rule, with the rule as it stood.

    ``(verdict_id, field)`` is deliberately **not** unique: one declaration is evaluated
    against several rules and each comparison is its own finding. ``(verdict_id, field,
    rule_id)`` is unique, and saying so requires ``rule_id`` as a column — inside the
    snapshot document it cannot carry a constraint.
    """

    __tablename__ = "field_findings"
    __table_args__ = (UniqueConstraint("verdict_id", "field", "rule_id"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    verdict_id: Mapped[UUID] = mapped_column(ForeignKey("verdicts.id"), nullable=False, index=True)

    field: Mapped[DeclarationField] = mapped_column(
        enum_column(DeclarationField, "declaration_field"), nullable=False
    )

    rule_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    """Which rule produced this finding, copied out of :attr:`rule_snapshot`.

    Written from ``rule_snapshot["rule_id"]`` and never from anywhere else: the snapshot
    stays the record of what was applied and this is a queryable copy of one field of it.
    It earns a column because the officer dashboard filters and groups by rule, and
    because the uniqueness above cannot be stated without it. Not a foreign key — there
    is no rules table to point at, and there must not be one.
    """

    state: Mapped[FieldState] = mapped_column(
        enum_column(FieldState, "field_state"), nullable=False
    )
    """The per-field outcome, always supplied by the caller: not null, no Python default,
    no server default. The module docstring says why the database may supply none."""

    reason: Mapped[str] = mapped_column(Text, nullable=False)
    observed_value: Mapped[str | None] = mapped_column(Text)
    expected_value: Mapped[str | None] = mapped_column(Text)

    rule_snapshot: Mapped[dict[str, Any]] = mapped_column(Json, nullable=False)
    """A whole :class:`app.contracts.RuleParameterSnapshot`, by value.

    Written with ``model_dump(mode="json")`` and read with ``model_validate``. The mode
    matters: a plain dump leaves ``Decimal`` and enum objects the driver cannot adapt,
    and a tolerance that became a float on the way to disk corrupts the comparison that
    decides a finding.
    """

    evidence_span_ids: Mapped[list[str]] = mapped_column(Json, nullable=False, default=list)
    evidence_regions: Mapped[list[dict[str, Any]]] = mapped_column(
        Json, nullable=False, default=list
    )
    """Polygons and bounding boxes for the pixels behind this finding. Cited and drawn,
    never queried, and not axis-aligned: a column per coordinate would be a schema change
    per capture geometry."""


class EvidenceEntryRow(Base):
    """One link of a scan's hash chain, stored as the bytes it was hashed from.

    The two type choices are the whole point of the table.
    :func:`app.modules.evidence.chain.compute_entry_hash` hashes the timestamp *string*,
    so ``timestamp`` is text: as a ``timestamptz`` it would be re-rendered on every read
    — ``Z`` against ``+00:00``, microseconds truncated — and verification would report a
    broken chain nobody had touched. ``compute_payload_hash`` likewise hashes canonical
    JSON bytes, and ``jsonb`` renormalises numeric literals and discards the original
    serialisation, so the payload is text too.

    ``UniqueConstraint(scan_id, sequence)`` is the storage-level answer to an inserted or
    reordered entry: enforced by the database, not by a caller remembering to check.
    """

    __tablename__ = "evidence_entries"
    __table_args__ = (UniqueConstraint("scan_id", "sequence"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    scan_id: Mapped[UUID] = mapped_column(ForeignKey("scans.id"), nullable=False, index=True)

    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(SHA256_HEX_LENGTH), nullable=False)
    prev_hash: Mapped[str] = mapped_column(String(SHA256_HEX_LENGTH), nullable=False)
    entry_hash: Mapped[str] = mapped_column(String(SHA256_HEX_LENGTH), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)

    asset_type: Mapped[EvidenceAssetType] = mapped_column(
        enum_column(EvidenceAssetType, "evidence_asset_type"), nullable=False
    )
    """What this entry holds, and therefore when it may be destroyed.

    Required with no default, on the column as well as the model. A default would let an
    entry carry a disposition nobody chose, on the one field that decides whether evidence
    is destroyed. It is also inside the entry hash, so a relabelling breaks verification
    rather than silently moving the entry to a different retention rule."""

    storage_ref: Mapped[str | None] = mapped_column(String(512))
    """Where the full artefact sits in the object store, when one was written. ``None``
    when the payload is held inline and nothing was uploaded."""


class ReviewRow(Base):
    """One officer action on one verdict. The human confirmation step, as a record.

    **Append-only in shape, not merely in intent.** There is no UPDATE path: the
    repository exposes an insert and a select and nothing else. A reversal or a correction
    is a *new* row whose :attr:`supersedes_id` names the row it replaces, the same way the
    evidence chain handles a correction — because a review that can be edited is a review
    an officer cannot be shown to have made.

    That shape is what makes the guarantee structural. A scan is finalised exactly when a
    row exists here carrying CONFIRM, REJECT or OVERRIDE. It is not a column on
    :class:`Scan` that some later background job could set, and there is no state a scan
    can reach on its own that means an officer agreed with it.
    """

    __tablename__ = "reviews"
    __table_args__ = (Index("ix_reviews_scan_id_created_at", "scan_id", "created_at"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    scan_id: Mapped[UUID] = mapped_column(ForeignKey("scans.id"), nullable=False, index=True)
    verdict_id: Mapped[UUID] = mapped_column(ForeignKey("verdicts.id"), nullable=False)
    """Which verdict was reviewed. Re-evaluating a scan writes a second verdict, so a
    review that named only the scan would not say what the officer actually looked at."""

    action: Mapped[ReviewAction] = mapped_column(
        enum_column(ReviewAction, "review_action"), nullable=False
    )

    officer_id: Mapped[str] = mapped_column(String(JURISDICTION_LEVEL_LENGTH), nullable=False)
    """The reviewing officer's :attr:`app.core.rbac.Principal.subject`. Not a foreign key
    for the same reason :attr:`Scan.officer_id` is not: officers are configuration until
    there is a users table."""

    note: Mapped[str | None] = mapped_column(Text)
    """The officer's own words. Required by the route for every action but CONFIRM — a
    rejection or an override with no stated reason is not reviewable by anyone else."""

    overridden_verdict: Mapped[Verdict | None] = mapped_column(enum_column(Verdict, "verdict"))
    """The verdict the officer substituted, for OVERRIDE and nothing else.

    Still one of the three: an officer's substitution is a recommendation reaching an
    enforcement workflow, not a legal determination, so there is no member here that the
    automated path could not also have produced.
    """

    supersedes_id: Mapped[UUID | None] = mapped_column(ForeignKey("reviews.id"))
    """The review this one corrects, where it corrects one. Both rows stay."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
