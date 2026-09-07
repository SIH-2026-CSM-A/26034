"""The tables written about a package by someone outside the enforcement chain.

An officer escalating a verdict to a manufacturer, and a member of the public reporting
their own experience of a product. Neither is on the scan path, and neither produces or
alters a verdict.

The two guarantees to read before editing anything here:

**:class:`ComplaintRow` is append-only in shape.** There is no UPDATE path. A transition is
a new row whose ``supersedes_id`` names the one it replaces, the same way
:class:`app.core.models.ReviewRow` handles a correction.

**:class:`ProductReviewRow` holds no reviewer identity of any kind.** Not "held elsewhere"
and not "hashed" — there is no column from which a submitter can be recovered or two
submissions linked. The anonymity is structural: there is no field to leak.

The vocabularies live in :mod:`app.core.enums` and the column plumbing in
:mod:`app.core.schema`, the same division ``models.py`` follows.
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import ComplaintStatus, ConsumerSafetyClaim
from app.core.schema import JURISDICTION_LEVEL_LENGTH, Base, enum_column

BARCODE_LENGTH = 64
"""Column width for a product barcode. Comfortably above GTIN-14, the longest of the
formats a package carries, without pretending to validate one."""


class ComplaintRow(Base):
    """One officer's escalation to a manufacturer about one verdict.

    **Append-only in shape, not merely in intent.** A complaint that moves from RAISED to
    ACKNOWLEDGED is a *second row* carrying ACKNOWLEDGED whose :attr:`supersedes_id` names
    the first, and a complaint reopened after a resolution is a fourth row naming the third.
    Every row stays. The head of a thread is the row nothing supersedes; there is no
    ``is_current`` flag and no unique index, because a flag is a column a background job can
    set and the point is that nothing but a new row changes what an officer recorded.

    :attr:`status` therefore reads as *the state this row asserts*, not as a field that
    moves — exactly as :attr:`app.core.models.ReviewRow.action` is what the officer did
    rather than the review's condition. Storing it that way is what makes the escalation
    history reconstructable; a mutable status column would leave only the latest answer.

    A superseding row restates :attr:`scan_id`, :attr:`verdict_id`,
    :attr:`manufacturer_name` and :attr:`issue_summary` by value rather than joining back
    through :attr:`supersedes_id`, the same way a verdict snapshots its rule parameters:
    what was escalated must not change because a later row was written.

    There is deliberately no ``resolved_at``. On an append-only table a resolution is a new
    row carrying RESOLVED, so a resolution timestamp would be a copy of that row's own
    :attr:`raised_at` — a duplicate that can drift from the column beside it, buying no
    constraint and saving no join. Resolution time is ``raised_at`` on the RESOLVED row.
    """

    __tablename__ = "complaints"
    __table_args__ = (Index("ix_complaints_scan_id_raised_at", "scan_id", "raised_at"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    scan_id: Mapped[UUID] = mapped_column(ForeignKey("scans.id"), nullable=False, index=True)

    verdict_id: Mapped[UUID] = mapped_column(ForeignKey("verdicts.id"), nullable=False)
    """Which verdict was escalated. Re-evaluating a scan writes a second verdict, so a
    complaint naming only the scan would not say what the officer actually escalated — the
    same reason :attr:`app.core.models.ReviewRow.verdict_id` exists."""

    manufacturer_name: Mapped[str] = mapped_column(Text, nullable=False)
    """The manufacturer as the package declared them, by value.

    Not a foreign key, and there is no manufacturers table: this is a snapshot of what the
    label said when the escalation was raised. A later correction to a registry must not
    silently restate who was escalated to."""

    issue_summary: Mapped[str] = mapped_column(Text, nullable=False)
    """The officer's own words. Required: an escalation with no stated reason is not
    answerable by the manufacturer or reviewable by anyone else."""

    status: Mapped[ComplaintStatus] = mapped_column(
        enum_column(ComplaintStatus, "complaint_status"), nullable=False
    )
    """The state this row asserts. NOT NULL with no default of any kind — storage may not
    invent the state of an escalation, for the same reason it may not invent a verdict."""

    raised_by_officer_id: Mapped[str] = mapped_column(
        String(JURISDICTION_LEVEL_LENGTH), nullable=False
    )
    """The officer's :attr:`app.core.rbac.Principal.subject`. Not a foreign key, for the
    same reason :attr:`app.core.models.Scan.officer_id` is not: officers are configuration
    until there is a users table.

    On a superseding row this is the officer who recorded *that* event, not the one who
    opened the thread — that officer is on the row this one supersedes, which is one of the
    things keeping both rows buys."""

    raised_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    """When **this row** was recorded. On the first row of a thread that is when the
    complaint was raised; on a superseding row it is when that transition was recorded, and
    on the RESOLVED row it is when the escalation closed."""

    supersedes_id: Mapped[UUID | None] = mapped_column(ForeignKey("complaints.id"))
    """The row this one replaces, where it replaces one. Both rows stay."""


class ProductReviewRow(Base):
    """One consumer's report about one barcode. **Holds no reviewer identity at all.**

    Not "identity is stored elsewhere" and not "identity is hashed": there is no column here
    from which a submitter can be recovered or two submissions linked, and this table has no
    foreign keys in either direction. The forbidden set is named rather than implied,
    because every one of them arrives with a good reason attached — no user id, no officer
    id, no IP address, no hash or truncation of an IP address, no device or browser
    fingerprint, no session id, no email, and no salted derivative of any of them. A SHA-256
    of an IPv4 address is a 32-bit search space; hashing it makes it look private without
    making it private.

    The accepted cost is that submissions cannot be deduplicated. That is the trade this
    table makes deliberately: a publication threshold that can be gamed is cheaper than a
    consumer-facing database that can be compelled to say who reported what.
    """

    __tablename__ = "product_reviews"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)

    product_identifier: Mapped[str] = mapped_column(
        String(BARCODE_LENGTH), nullable=False, index=True
    )
    """The barcode as scanned — EAN-13, UPC-A or GTIN-14 — as a string, because a leading
    zero is part of the code and an integer would eat it. Indexed: "the reports for this
    barcode" is the only query this table has, and a publication count runs off the same
    index."""

    consumer_safety_claim: Mapped[ConsumerSafetyClaim] = mapped_column(
        enum_column(ConsumerSafetyClaim, "consumer_safety_claim"), nullable=False
    )
    """What the consumer asserted. **Not a verdict**, which is why neither the column nor
    its type carries that word: "verdict" is reserved for the rule engine's output, and a
    crowd consensus must never render as a compliance one. Its own PostgreSQL type, never
    the ``verdict`` type — the database refuses ``POTENTIAL_VIOLATION`` here and refuses
    ``unsafe`` in a verdict column, in both directions.

    NOT NULL with no default: there is no claim storage is entitled to invent on a
    consumer's behalf."""

    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    """When the report arrived.

    The strongest linkage vector left on this table is not a column: this instant, taken
    with :attr:`product_identifier` and correlated against a web access log, identifies a
    submitter. The mitigation belongs to the submission route, which must not log the
    request that created the row. Nothing in the schema can close it."""

    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    """When this report became publicly visible, or ``None`` while it is held.

    **The NULL is the whole publication mechanism.** No ``is_published`` boolean, no
    moderation status, no queue table: a report is held until enough reports exist for its
    barcode, and publishing is stamping this column. The threshold is a rule and does not
    live in ``core``; this file states only that the column exists and that NULL means
    held."""

    anonymous_token: Mapped[UUID] = mapped_column(Uuid, nullable=False, unique=True, default=uuid4)
    """A fresh random value per row, derived from nothing.

    Typed ``Uuid`` and not a hex string precisely so it cannot hold a digest of something
    about the submitter. Putting one there would need a column type change, which is a
    migration, which is a review gate.

    **Unique**, and the uniqueness is not about collisions — a version 4 UUID does not need
    one. It is there so that the improvement this column will one day attract, reusing a
    token across a submitter's reports in order to deduplicate them, fails on the second
    INSERT instead of passing code review.

    It is not a deduplication key, and there is no deduplication of consumer reports.
    """
