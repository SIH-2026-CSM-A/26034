"""The CORE-004 tables as PostgreSQL actually builds them.

Only what SQLite cannot prove: that the migration puts the declared columns on the real
database, that the native enum types refuse what they should, and that the four tables
survive a round trip through the async session the application uses.

``tests/core/test_market.py`` and ``tests/core/test_complaints.py`` prove the mapping and
the schema properties; repeating either here would make these tests fail for their reasons.
"""

from datetime import UTC, datetime
from uuid import uuid4

import psycopg
import pytest
import sqlalchemy
from alembic.config import Config
from sqlalchemy import inspect, select, text

from app.core.complaints import ComplaintRow, ProductReviewRow
from app.core.enums import ComplaintStatus, ConsumerSafetyClaim, VendorType
from app.core.market import VendorRow, VendorScanRow
from tests.core.test_persistence import a_scan
from tests.persistence.conftest import request_session

pytestmark = pytest.mark.postgres

BARCODE = "8901234567890"

EXPECTED_COLUMNS: dict[str, dict[str, bool]] = {
    "vendors": {
        "id": False,
        "name": False,
        "vendor_type": False,
        "state": False,
        "region": True,
        "district": True,
        "created_at": False,
    },
    "vendor_scans": {
        "scan_id": False,
        "vendor_id": False,
        "created_at": False,
    },
    "complaints": {
        "id": False,
        "scan_id": False,
        "verdict_id": False,
        "manufacturer_name": False,
        "issue_summary": False,
        "status": False,
        "raised_by_officer_id": False,
        "raised_at": False,
        "supersedes_id": True,
    },
    "product_reviews": {
        "id": False,
        "product_identifier": False,
        "consumer_safety_claim": False,
        "submitted_at": False,
        "published_at": True,
        "anonymous_token": False,
    },
}
"""Column name to nullability, per table, written out here rather than read from the models.

Written by hand on purpose. Comparing the database against ``Base.metadata`` is what
``alembic check`` already does; a test that derived this from the models would compare the
models with themselves and stay green through any change made to both at once. These are
the columns CORE-004 says the four tables have, and the only nullable ones are the three
that carry meaning as NULL: a vendor's unrecorded ``region`` and ``district``, a
complaint's ``supersedes_id`` when it supersedes nothing, and a report's ``published_at``
while it is held.
"""


def columns_in(database_url: str, table: str) -> dict[str, bool]:
    """What the database says the table holds, read back rather than assumed."""
    engine = sqlalchemy.create_engine(database_url)
    try:
        with engine.connect() as connection:
            return {
                column["name"]: column["nullable"]
                for column in inspect(connection).get_columns(table)
            }
    finally:
        engine.dispose()


@pytest.mark.parametrize("table", sorted(EXPECTED_COLUMNS))
def test_the_migration_builds_every_declared_column(
    migrated: Config, database_url: str, table: str
) -> None:
    """Each table exists with exactly its expected columns and nullability.

    ``test_every_declared_table_reaches_the_database`` proves the table is there. Nothing
    proves what is in it: a column dropped from a model and from nothing else leaves that
    test green. This is the assertion that reads the columns back.
    """
    assert columns_in(database_url, table) == EXPECTED_COLUMNS[table]


async def test_a_scan_cannot_take_a_second_vendor_attribution(
    migrated: Config, engine_disposed: None
) -> None:
    """The primary key does the work, and the violation is named rather than assumed.

    Asserting a bare ``DBAPIError`` would pass if the table did not exist, if a foreign key
    were violated, or if the column had the wrong type — none of which is the claim. The
    claim is that ``pk_vendor_scans`` refuses the second row, so that is what is asserted.
    """
    scan = a_scan("subject")
    vendor = VendorRow(
        id=uuid4(),
        name="Test Traders",
        vendor_type=VendorType.KIRANA,
        state="Maharashtra",
        region="Pune",
        district="Satara",
    )
    other = VendorRow(
        id=uuid4(),
        name="Other Traders",
        vendor_type=VendorType.GODOWN,
        state="Maharashtra",
        region="Pune",
        district="Satara",
    )

    async with request_session() as session:
        session.add_all([scan, vendor, other])
        await session.flush()
        session.add(VendorScanRow(scan_id=scan.id, vendor_id=vendor.id))
        await session.commit()

        session.add(VendorScanRow(scan_id=scan.id, vendor_id=other.id))
        with pytest.raises(sqlalchemy.exc.IntegrityError) as refused:
            await session.commit()
        assert isinstance(refused.value.orig, psycopg.errors.UniqueViolation)
        assert refused.value.orig.diag.constraint_name == "pk_vendor_scans"
        await session.rollback()


async def test_the_market_tables_round_trip_through_the_async_session(
    migrated: Config, engine_disposed: None
) -> None:
    """All four tables, one transaction, through the session a request handler gets.

    One round trip rather than one per column: what is under test is the machinery — the
    native enum types coming back as Python members and the tz-aware instants surviving —
    and repeating it per column proves the same thing again.
    """
    async with request_session() as session:
        scan = a_scan("subject")
        vendor = VendorRow(
            id=uuid4(),
            name="Test Traders",
            vendor_type=VendorType.KIRANA,
            state="Maharashtra",
            region="Pune",
            district="Satara",
        )
        session.add_all([scan, vendor])
        await session.flush()

        session.add(VendorScanRow(scan_id=scan.id, vendor_id=vendor.id))

        verdict_id = (
            await session.execute(
                text(
                    "insert into verdicts "
                    "(id, scan_id, verdict, subject_ref, rule_set_version, evaluated_at, "
                    " field_providers) "
                    "values (gen_random_uuid(), :scan_id, 'REVIEW', :subject, '2026.09.1', "
                    " now(), '{}'::jsonb) returning id"
                ),
                {"scan_id": scan.id, "subject": str(scan.id)},
            )
        ).scalar_one()

        raised = ComplaintRow(
            id=uuid4(),
            scan_id=scan.id,
            verdict_id=verdict_id,
            manufacturer_name="Example Foods Private Limited",
            issue_summary="Net quantity declaration is not legible.",
            status=ComplaintStatus.RAISED,
            raised_by_officer_id="inspector",
        )
        session.add(raised)
        await session.flush()
        session.add(
            ComplaintRow(
                id=uuid4(),
                scan_id=scan.id,
                verdict_id=verdict_id,
                manufacturer_name="Example Foods Private Limited",
                issue_summary="Net quantity declaration is not legible.",
                status=ComplaintStatus.ACKNOWLEDGED,
                raised_by_officer_id="inspector",
                supersedes_id=raised.id,
            )
        )

        session.add(
            ProductReviewRow(
                product_identifier=BARCODE,
                consumer_safety_claim=ConsumerSafetyClaim.UNSAFE,
            )
        )
        session.add(
            ProductReviewRow(
                product_identifier=BARCODE,
                consumer_safety_claim=ConsumerSafetyClaim.SAFE,
                published_at=datetime(2026, 9, 7, 12, 0, tzinfo=UTC),
            )
        )
        await session.commit()

        stored_vendor = await session.get(VendorRow, vendor.id)
        assert stored_vendor is not None
        assert stored_vendor.vendor_type is VendorType.KIRANA
        assert stored_vendor.created_at.tzinfo is not None

        attribution = await session.get(VendorScanRow, scan.id)
        assert attribution is not None
        assert attribution.vendor_id == vendor.id

        complaints = (
            await session.scalars(select(ComplaintRow).order_by(ComplaintRow.raised_at))
        ).all()
        assert len(complaints) == 2
        assert complaints[0].status is ComplaintStatus.RAISED
        assert complaints[1].status is ComplaintStatus.ACKNOWLEDGED
        assert complaints[1].supersedes_id == raised.id

        reports = (
            await session.scalars(select(ProductReviewRow).order_by(ProductReviewRow.published_at))
        ).all()
        assert {report.consumer_safety_claim for report in reports} == {
            ConsumerSafetyClaim.SAFE,
            ConsumerSafetyClaim.UNSAFE,
        }
        assert sum(report.published_at is None for report in reports) == 1
        assert len({report.anonymous_token for report in reports}) == 2


async def test_the_consumer_claim_type_refuses_a_system_verdict(
    migrated: Config, engine_disposed: None
) -> None:
    """The database itself will not store a compliance verdict as a consumer's claim.

    This is the structural half of the naming decision. ``consumer_safety_claim`` is its
    own type and not ``verdict``, so a crowd report cannot be written into the vocabulary
    the rule engine speaks, whatever a future caller intends.

    The expected error is specifically an invalid *value* for the type: if the type had
    never been created the cast would still fail, with ``UndefinedObject``, and a test that
    only asked for a ``DBAPIError`` would pass without proving anything.
    """
    async with request_session() as session:
        with pytest.raises(sqlalchemy.exc.DBAPIError) as refused:
            await session.execute(text("select 'POTENTIAL_VIOLATION'::consumer_safety_claim"))
        assert isinstance(refused.value.orig, psycopg.errors.InvalidTextRepresentation)
        await session.rollback()


async def test_the_verdict_type_refuses_a_consumer_claim(
    migrated: Config, engine_disposed: None
) -> None:
    """And the other direction, which is what makes the two vocabularies non-interchangeable."""
    async with request_session() as session:
        with pytest.raises(sqlalchemy.exc.DBAPIError) as refused:
            await session.execute(text("select 'unsafe'::verdict"))
        assert isinstance(refused.value.orig, psycopg.errors.InvalidTextRepresentation)
        await session.rollback()


@pytest.mark.parametrize(
    ("type_name", "outsider"),
    [
        ("vendor_type", "hypermarket"),
        ("complaint_status", "probably_fine"),
        ("consumer_safety_claim", "mostly_safe"),
    ],
)
async def test_each_new_enum_type_refuses_a_value_outside_its_members(
    migrated: Config, engine_disposed: None, type_name: str, outsider: str
) -> None:
    """The database's own guard, which exists only because the columns are native types.

    A ``VARCHAR`` would accept whatever a caller happened to send.
    """
    async with request_session() as session:
        with pytest.raises(sqlalchemy.exc.DBAPIError) as refused:
            await session.execute(text(f"select '{outsider}'::{type_name}"))
        assert isinstance(refused.value.orig, psycopg.errors.InvalidTextRepresentation)
        await session.rollback()
