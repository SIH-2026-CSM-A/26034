"""What the complaint and consumer-report tables promise, proved against a real database.

Sync ``Session`` on in-memory SQLite, the same substrate and the same reasoning as
``tests/core/test_market.py``. The native enum types, and that the database refuses a
system verdict in a consumer column, are proved in ``tests/persistence/``.

Every test here runs once per designation profile (see ``conftest.py``).
"""

from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.complaints import ComplaintRow, ProductReviewRow
from app.core.enums import ComplaintStatus, ConsumerSafetyClaim
from app.core.models import Base, Scan, VerdictRow
from tests.core.test_persistence import a_scan, a_verdict

BARCODE = "8901234567890"
"""One EAN-13, written here rather than generated. Not a real product."""


@pytest.fixture
def db() -> Iterator[Session]:
    """An empty database carrying the schema under test."""
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


@pytest.fixture
def escalatable(db: Session) -> tuple[Scan, VerdictRow]:
    """A scan and the verdict on it, which is the minimum a complaint can name."""
    scan = a_scan("subject")
    return scan, a_verdict(db, scan)


def a_complaint(
    scan: Scan,
    verdict: VerdictRow,
    status: ComplaintStatus,
    supersedes_id: UUID | None = None,
) -> ComplaintRow:
    """One row of an escalation thread. Everything not under test takes a fixed value."""
    return ComplaintRow(
        id=uuid4(),
        scan_id=scan.id,
        verdict_id=verdict.id,
        manufacturer_name="Example Foods Private Limited",
        issue_summary="Net quantity declaration is not legible on the principal display panel.",
        status=status,
        raised_by_officer_id="inspector",
        supersedes_id=supersedes_id,
    )


def test_a_complaint_transition_is_a_new_row_and_the_first_one_still_says_raised(
    db: Session, escalatable: tuple[Scan, VerdictRow]
) -> None:
    """Append-only in shape: acknowledging a complaint writes a row, it does not edit one.

    The assertion that matters is the last one. A mutable ``status`` column would leave
    only the latest answer, and the escalation history — who recorded what, and when —
    would not be reconstructable. Here row A still reads RAISED forever.
    """
    scan, verdict = escalatable

    raised = a_complaint(scan, verdict, ComplaintStatus.RAISED)
    db.add(raised)
    db.commit()

    acknowledged = a_complaint(scan, verdict, ComplaintStatus.ACKNOWLEDGED, supersedes_id=raised.id)
    db.add(acknowledged)
    db.commit()

    rows = db.scalars(select(ComplaintRow).order_by(ComplaintRow.status)).all()
    assert len(rows) == 2

    db.refresh(raised)
    assert raised.status is ComplaintStatus.RAISED
    assert raised.supersedes_id is None
    assert acknowledged.supersedes_id == raised.id


def test_a_reopened_complaint_supersedes_the_resolved_one(
    db: Session, escalatable: tuple[Scan, VerdictRow]
) -> None:
    """The case the append-only shape exists for, and the one a status column loses.

    Four rows, and the head of the thread is the row nothing supersedes. Resolution time is
    ``raised_at`` on the RESOLVED row — there is no ``resolved_at`` column, because on this
    shape it would duplicate that value and could drift from it.
    """
    scan, verdict = escalatable

    chain: list[ComplaintRow] = []
    previous: UUID | None = None
    for status in (
        ComplaintStatus.RAISED,
        ComplaintStatus.ACKNOWLEDGED,
        ComplaintStatus.RESOLVED,
        ComplaintStatus.RAISED,
    ):
        row = a_complaint(scan, verdict, status, supersedes_id=previous)
        db.add(row)
        db.commit()
        chain.append(row)
        previous = row.id

    assert len(db.scalars(select(ComplaintRow)).all()) == 4

    superseded = {row.supersedes_id for row in chain} - {None}
    heads = [row for row in chain if row.id not in superseded]
    assert len(heads) == 1
    assert heads[0] is chain[-1]
    assert heads[0].status is ComplaintStatus.RAISED

    resolved = chain[2]
    assert resolved.status is ComplaintStatus.RESOLVED
    assert resolved.raised_at is not None


def test_the_complaints_table_holds_exactly_its_declared_columns() -> None:
    """Exact set, so a column added or dropped without a migration turns this red.

    ``resolved_at`` is deliberately absent and this is what keeps it absent: on an
    append-only table a resolution is a new row, so a resolution timestamp would be a copy
    of that row's own ``raised_at``.
    """
    assert set(ComplaintRow.__table__.c.keys()) == {
        "id",
        "scan_id",
        "verdict_id",
        "manufacturer_name",
        "issue_summary",
        "status",
        "raised_by_officer_id",
        "raised_at",
        "supersedes_id",
    }


def test_product_reviews_carries_no_reviewer_identity() -> None:
    """The anonymity guarantee, as a property of the schema rather than of one insert.

    Asserted as an **exact set**, not a denylist. A denylist cannot anticipate the name
    someone gives the column they add — ``ip_hash``, ``device_fingerprint``,
    ``submitter_key``, each arriving with a good reason attached — and the guarantee is not
    "these particular columns are absent" but "there is no field to leak". Any addition at
    all turns this red and has to argue for itself.

    The second assertion says the same thing about references: this table points at nothing
    and nothing points at it, so a submitter cannot be reached by a join either.
    """
    assert set(ProductReviewRow.__table__.c.keys()) == {
        "id",
        "product_identifier",
        "consumer_safety_claim",
        "submitted_at",
        "published_at",
        "anonymous_token",
    }
    assert ProductReviewRow.__table__.foreign_keys == set()


def test_a_held_report_is_held_by_a_null_and_by_nothing_else() -> None:
    """``published_at`` NULL is the whole publication mechanism.

    No ``is_published`` boolean, no moderation status, no queue table — so there is no
    second place that can disagree with this column about whether a report is visible.
    """
    published_at = ProductReviewRow.__table__.c.published_at
    assert published_at.nullable is True
    assert published_at.default is None
    assert published_at.server_default is None

    columns = set(ProductReviewRow.__table__.c.keys())
    assert not columns & {"is_published", "published", "status", "moderation_status", "visible"}


def test_a_held_report_and_a_published_one_round_trip(db: Session) -> None:
    """The NULL survives storage, and stamping it is what publishes the report."""
    held = ProductReviewRow(
        product_identifier=BARCODE, consumer_safety_claim=ConsumerSafetyClaim.UNSAFE
    )
    published = ProductReviewRow(
        product_identifier=BARCODE,
        consumer_safety_claim=ConsumerSafetyClaim.SAFE,
        published_at=datetime(2026, 9, 7, 12, 0, tzinfo=UTC),
    )
    db.add_all([held, published])
    db.commit()

    assert held.published_at is None
    assert published.published_at is not None
    assert held.anonymous_token != published.anonymous_token


def test_two_reports_cannot_share_an_anonymous_token(db: Session) -> None:
    """The uniqueness is not about collisions — a version 4 UUID does not need one.

    It is there so that reusing one token across a submitter's reports, in order to
    deduplicate them, fails on the second INSERT rather than passing code review. This is
    that INSERT.
    """
    token = uuid4()
    db.add(
        ProductReviewRow(
            product_identifier=BARCODE,
            consumer_safety_claim=ConsumerSafetyClaim.SAFE,
            anonymous_token=token,
        )
    )
    db.commit()

    db.add(
        ProductReviewRow(
            product_identifier=BARCODE,
            consumer_safety_claim=ConsumerSafetyClaim.UNSAFE,
            anonymous_token=token,
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_no_outcome_column_has_a_value_the_database_could_supply() -> None:
    """Neither a complaint's state nor a consumer's claim is storage's to invent.

    The same property ``test_no_outcome_column_has_a_value_the_database_could_supply`` in
    ``test_persistence.py`` asserts of ``FieldFindingRow.state`` and ``VerdictRow.verdict``,
    for the same reason: a ``server_default`` on either of these would put an assertion
    nobody made on the record.
    """
    for column in (
        ComplaintRow.__table__.c.status,
        ProductReviewRow.__table__.c.consumer_safety_claim,
    ):
        assert column.nullable is False
        assert column.default is None
        assert column.server_default is None
