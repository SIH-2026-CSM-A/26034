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

The jurisdiction columns and the evidence-chain column types are equally load-bearing and
are explained on the columns themselves. ``core/README.md`` carries all of it in full.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.contracts import DeclarationField, FieldState, Verdict

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
"""Names every constraint and index deterministically. Without it SQLAlchemy emits
unnamed constraints, autogenerate cannot refer to them, and a downgrade has nothing to
drop."""

Json = JSON().with_variant(JSONB(), "postgresql")
"""``jsonb`` on PostgreSQL, ``JSON`` on anything else. One annotation, both dialects."""

JURISDICTION_LEVEL_LENGTH = 120
"""Column width for a state, region or district name."""

SHA256_HEX_LENGTH = 64
"""A SHA-256 digest as :func:`hashlib.sha256().hexdigest` renders it."""


def _enum(python_enum: type[StrEnum], name: str) -> Enum:
    """A closed vocabulary the database enforces.

    A native ``TYPE`` on PostgreSQL and a ``VARCHAR`` with a ``CHECK`` elsewhere.
    ``values_callable`` stores each member's *value*; SQLAlchemy stores names by default,
    which for the enums here whose name and value differ would put the wrong string on
    disk.
    """
    return Enum(
        python_enum,
        name=name,
        create_constraint=True,
        values_callable=lambda enum: [member.value for member in enum],
    )


class ScanSourceType(StrEnum):
    """Which ingestion path a scan arrived by.

    Both are first-class. A listing is not an image that failed to be an image, and
    modelling it as its own source type is what keeps a marketplace adapter an adapter.
    """

    PHYSICAL_LABEL = "physical_label"
    """An image of a package captured by an officer."""

    CATALOGUE_RECORD = "catalogue_record"
    """A structured listing — see :class:`app.contracts.CatalogueRecord`."""


class ScanStatus(StrEnum):
    """Where a scan has got to. Processing state, never a compliance outcome."""

    RECEIVED = "received"
    """Accepted and stored; evaluation has not started."""

    PROCESSING = "processing"
    """Somewhere between the quality gate and verdict assembly."""

    COMPLETE = "complete"
    """Evaluation finished and a verdict was written. Says nothing about what it was."""

    FAILED = "failed"
    """Processing did not finish. Distinct from every verdict: a scan that crashed has
    no finding about the package at all."""


class CalibrationMethod(StrEnum):
    """What basis, if any, exists for a physical measurement of this scan.

    Recorded at capture because it decides whether a millimetre figure may be emitted at
    all. Typed rather than buried in :attr:`Scan.capture_metadata` for that reason — a
    value that gates a legal output is queryable and constrained, not a key in a blob.
    """

    ARTWORK = "artwork"
    """Pre-print artwork was supplied; physical sizes are known exactly."""

    REFERENCE_OBJECT = "reference_object"
    """An object of known dimensions is in frame, so a measurement carries an interval."""

    NONE = "none"
    """Neither. Measurement refuses and routes to review; it does not guess."""


class Base(DeclarativeBase):
    """Declarative base for every table in this schema. Alembic reads its metadata."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Scan(Base):
    """One package or listing submitted for evaluation, and where it came from."""

    __tablename__ = "scans"
    __table_args__ = (Index("ix_scans_state_region_district", "state", "region", "district"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    source_type: Mapped[ScanSourceType] = mapped_column(
        _enum(ScanSourceType, "scan_source_type"), nullable=False
    )
    status: Mapped[ScanStatus] = mapped_column(_enum(ScanStatus, "scan_status"), nullable=False)
    calibration_method: Mapped[CalibrationMethod] = mapped_column(
        _enum(CalibrationMethod, "calibration_method"), nullable=False
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

    verdict: Mapped[Verdict] = mapped_column(_enum(Verdict, "verdict"), nullable=False)
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
        _enum(DeclarationField, "declaration_field"), nullable=False
    )

    rule_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    """Which rule produced this finding, copied out of :attr:`rule_snapshot`.

    Written from ``rule_snapshot["rule_id"]`` and never from anywhere else: the snapshot
    stays the record of what was applied and this is a queryable copy of one field of it.
    It earns a column because the officer dashboard filters and groups by rule, and
    because the uniqueness above cannot be stated without it. Not a foreign key — there
    is no rules table to point at, and there must not be one.
    """

    state: Mapped[FieldState] = mapped_column(_enum(FieldState, "field_state"), nullable=False)
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

    storage_ref: Mapped[str | None] = mapped_column(String(512))
    """Where the full artefact sits in the object store, when one was written. ``None``
    when the payload is held inline and nothing was uploaded."""
