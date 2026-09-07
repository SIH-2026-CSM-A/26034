"""What the vendor tables promise, proved against a real database.

The substrate is a sync ``Session`` on in-memory SQLite, the same split
``tests/core/test_persistence.py`` documents: what this file proves — which column holds
what, and that a scoped SELECT over ``vendors`` narrows the way one over ``scans`` does —
is not dialect-specific. The native enum types and the async session are proved in
``tests/persistence/``.

Every test here runs once per designation profile (see ``conftest.py``).
"""

from collections.abc import Iterator
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.enums import VendorType
from app.core.market import VendorRow, VendorScanRow
from app.core.models import Base, Scan
from app.core.rbac import Principal, scope_to_jurisdiction
from tests.core.conftest import CONTROLLER, DEPUTY, INSPECTOR, RECORDS
from tests.core.test_persistence import a_scan

VENDOR_IDS = {label: UUID(int=100 + index) for index, (label, *_) in enumerate(RECORDS)}
"""One stable id per jurisdiction fixture, so a result set can be named in assertions."""

VENDOR_LABELS = {vendor_id: label for label, vendor_id in VENDOR_IDS.items()}


@pytest.fixture
def db() -> Iterator[Session]:
    """An empty database carrying the schema under test.

    Duplicated from ``test_persistence.py`` rather than lifted into ``conftest.py``: that
    file defines its own throwaway ``Base`` for the RBAC tests, and importing this one
    beside it would collide.
    """
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def a_vendor(
    label: str = "subject",
    state: str = "Maharashtra",
    region: str | None = "Pune",
    district: str | None = "Satara",
) -> VendorRow:
    """One vendor in a named jurisdiction. Everything not under test takes a fixed value."""
    return VendorRow(
        id=VENDOR_IDS.get(label, UUID(int=999)),
        name="Test Traders",
        vendor_type=VendorType.KIRANA,
        state=state,
        region=region,
        district=district,
    )


def visible_vendors(db: Session, principal: Principal) -> set[str]:
    """Run the scoped SELECT the way an endpoint would and collect what came back."""
    statement = scope_to_jurisdiction(select(VendorRow), principal, VendorRow)
    return {VENDOR_LABELS[vendor.id] for vendor in db.scalars(statement)}


def visible_scans(db: Session, principal: Principal) -> set[str]:
    """The same query against ``scans``, for the parity assertion."""
    statement = scope_to_jurisdiction(select(Scan), principal, Scan)
    return {scan.officer_id for scan in db.scalars(statement)}


def test_scoping_narrows_vendors_exactly_as_it_narrows_scans(db: Session) -> None:
    """The jurisdiction columns on ``vendors`` are a contract with ``scope_to_jurisdiction``.

    That function reaches ``state``, ``region`` and ``district`` by ``getattr`` using the
    ``RoleTier`` member values, so this is what proves the three columns are named right:
    rename one and the call raises ``AttributeError`` here and nowhere else.

    It asserts parity rather than a fixed set. The claim CORE-004 makes is not "vendors
    scope correctly" in isolation but "vendors and scans agree about what a jurisdiction
    is" — a table stricter or looser than ``scans`` produces a query matching the wrong
    rows rather than an error, and only comparing the two catches that.
    """
    for label, state, region, district in RECORDS:
        db.add(a_vendor(label, state=state, region=region, district=district))
        # ``officer_id`` carries the label so the two result sets are comparable.
        scan = a_scan(label, state=state, region=region, district=district)
        scan.id = uuid4()
        scan.officer_id = label
        db.add(scan)
    db.commit()

    for principal in (INSPECTOR, DEPUTY, CONTROLLER):
        assert visible_vendors(db, principal) == visible_scans(db, principal), (
            f"{principal.tier.name} sees a different set of vendors than of scans; the two "
            f"tables disagree about what a jurisdiction is"
        )


def test_a_district_officer_sees_exactly_the_vendors_in_their_district(db: Session) -> None:
    """Guards the parity test above, which would pass if both sides returned nothing.

    Pinned to literals written here rather than derived from ``RECORDS``, so a fixture
    change cannot quietly move the expectation with the result.
    """
    for label, state, region, district in RECORDS:
        db.add(a_vendor(label, state=state, region=region, district=district))
    db.commit()

    assert visible_vendors(db, INSPECTOR) == {"mh-pune-satara"}
    assert visible_vendors(db, DEPUTY) == {"mh-pune-pune", "mh-pune-satara", "mh-pune-solapur"}
    assert len(visible_vendors(db, CONTROLLER)) == 5


def test_a_vendor_with_no_district_is_absent_from_that_districts_officer(db: Session) -> None:
    """The consequence of the nullability, asserted rather than left to be discovered.

    ``NULL = 'Satara'`` is NULL and never true, so a vendor recorded without a district is
    invisible to every officer below state tier — including the one whose patch physically
    contains the premises. That is the same behaviour ``Scan`` documents, and it is the
    reason ``vendors`` mirrors it rather than being stricter. Whether onboarding may leave
    a district unset is VND-001's to decide; this states what happens if it does.
    """
    db.add(a_vendor("mh-pune-satara", state="Maharashtra", region="Pune", district="Satara"))
    db.add(a_vendor("mh-pune-pune", state="Maharashtra", region=None, district=None))
    db.commit()

    assert visible_vendors(db, INSPECTOR) == {"mh-pune-satara"}
    assert visible_vendors(db, DEPUTY) == {"mh-pune-satara"}
    assert visible_vendors(db, CONTROLLER) == {"mh-pune-satara", "mh-pune-pune"}


def test_a_vendor_attribution_carries_nothing_the_verdict_path_could_branch_on() -> None:
    """The ticket's central non-negotiable, as a property of the schema.

    Asserted as an **exact set** rather than a list of forbidden names: a denylist cannot
    anticipate what someone calls the column they add, and the whole guarantee is that a
    vendor-submitted scan is an ordinary scan. A ``submission_channel``, a ``trust_level``
    or a ``status`` here would each be a second verdict path, and each turns this red.
    """
    assert set(VendorScanRow.__table__.c.keys()) == {"scan_id", "vendor_id", "created_at"}

    # The other half of the same claim: nothing about a vendor reaches the scan itself.
    assert not [column for column in Scan.__table__.c if "vendor" in column.name]


def test_the_vendors_table_holds_exactly_its_declared_columns() -> None:
    """A column added or dropped without a migration turns this red before the database does."""
    assert set(VendorRow.__table__.c.keys()) == {
        "id",
        "name",
        "vendor_type",
        "state",
        "region",
        "district",
        "created_at",
    }


def test_a_scan_can_carry_only_one_vendor_attribution(db: Session) -> None:
    """ "At most one vendor per scan" is the primary key, not a constraint beside it."""
    scan = a_scan("subject")
    vendor = a_vendor("subject")
    other = a_vendor("other")
    other.id = UUID(int=888)
    db.add_all([scan, vendor, other])
    db.commit()

    db.add(VendorScanRow(scan_id=scan.id, vendor_id=vendor.id))
    db.commit()

    db.add(VendorScanRow(scan_id=scan.id, vendor_id=other.id))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_no_vendor_column_has_a_value_the_database_could_supply() -> None:
    """``vendor_type`` is not null and has no default of any kind.

    Storage may not invent what kind of premises a package came from, for the same reason
    it may not invent a verdict. The one column the database does supply is ``created_at``,
    which records when the row was written and is nobody's assertion about anything.
    """
    column = VendorRow.__table__.c.vendor_type
    assert column.nullable is False
    assert column.default is None
    assert column.server_default is None
