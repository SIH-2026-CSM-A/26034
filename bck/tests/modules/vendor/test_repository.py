"""Unit and integration tests for vendor repository under VND-001 Part B.

Proves:
1. Persisting a VendorSubmission stages VendorRow and VendorScanRow against an existing Scan.
2. Multiple scans from the same vendor reuse the VendorRow without duplicate key errors.
3. A scan cannot be attributed to more than one vendor (primary key constraint).
4. Looking up a vendor's jurisdiction by vendor_id reconstructs the Jurisdiction model
   for direct use in route_verdict.
5. Scoped lookup handles full jurisdictions, region-level, and state-level vendors.
6. Non-existent vendor lookups return None.
7. End-to-end integration connecting repository jurisdiction lookup with route_verdict.
8. Session boundary convention: repository stages and flushes; caller commits.
9. Query helpers get_vendor and get_vendor_scan retrieve persisted entities.
"""

from collections.abc import Iterator
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.contracts import Verdict
from app.core import (
    Jurisdiction,
    RoleTier,
    VendorRow,
    VendorScanRow,
    VendorType,
)
from app.core.models import Base
from app.modules.vendor.domain import VendorSubmission
from app.modules.vendor.repository import (
    get_vendor,
    get_vendor_jurisdiction,
    get_vendor_scan,
    lookup_vendor_jurisdiction,
    persist_vendor_scan,
    persist_vendor_submission,
    record_vendor_scan,
    record_vendor_submission,
)
from app.modules.vendor.service import route_verdict
from tests.core.test_persistence import a_scan


@pytest.fixture
def db() -> Iterator[Session]:
    """In-memory SQLite database carrying the complete schema."""
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def make_submission(
    vendor_id: UUID | None = None,
    name: str = "Sri Krishna Stores",
    vendor_type: VendorType = VendorType.KIRANA,
    state: str = "Karnataka",
    region: str | None = "South",
    district: str | None = "Bengaluru Urban",
    image_ref: str = "uploads/labels/sample.jpg",
) -> VendorSubmission:
    """Construct a valid VendorSubmission fixture."""
    return VendorSubmission(
        id=vendor_id or uuid4(),
        name=name,
        vendor_type=vendor_type,
        jurisdiction=Jurisdiction(state=state, region=region, district=district),
        image_reference=image_ref,
    )


@pytest.mark.asyncio
async def test_persist_vendor_scan_creates_vendor_and_attribution(db: Session) -> None:
    """persist_vendor_scan stages VendorRow and VendorScanRow linked to the scan."""
    scan = a_scan("test-scan-1")
    db.add(scan)
    db.commit()

    vendor_id = uuid4()
    submission = make_submission(
        vendor_id=vendor_id,
        name="Sri Krishna Stores",
        vendor_type=VendorType.KIRANA,
        state="Karnataka",
        region="South",
        district="Bengaluru Urban",
    )

    vendor_scan = await persist_vendor_scan(db, scan.id, submission)
    db.commit()

    assert vendor_scan.scan_id == scan.id
    assert vendor_scan.vendor_id == vendor_id

    stored_vendor = db.get(VendorRow, vendor_id)
    assert stored_vendor is not None
    assert stored_vendor.name == "Sri Krishna Stores"
    assert stored_vendor.vendor_type == VendorType.KIRANA
    assert stored_vendor.state == "Karnataka"
    assert stored_vendor.region == "South"
    assert stored_vendor.district == "Bengaluru Urban"

    stored_scan_row = db.get(VendorScanRow, scan.id)
    assert stored_scan_row is not None
    assert stored_scan_row.vendor_id == vendor_id


@pytest.mark.asyncio
async def test_persist_vendor_scan_reuses_existing_vendor(db: Session) -> None:
    """Multiple submissions from the same vendor link to the single VendorRow."""
    scan1 = a_scan("test-scan-1")
    scan2 = a_scan("test-scan-2")
    scan2.id = uuid4()
    db.add_all([scan1, scan2])
    db.commit()

    vendor_id = uuid4()
    submission1 = make_submission(vendor_id=vendor_id)
    submission2 = make_submission(vendor_id=vendor_id)

    await persist_vendor_scan(db, scan1.id, submission1)
    await persist_vendor_scan(db, scan2.id, submission2)
    db.commit()

    vendors = db.scalars(select(VendorRow)).all()
    assert len(vendors) == 1
    assert vendors[0].id == vendor_id

    attributions = db.scalars(select(VendorScanRow)).all()
    assert len(attributions) == 2
    assert {row.scan_id for row in attributions} == {scan1.id, scan2.id}
    assert all(row.vendor_id == vendors[0].id for row in attributions)


@pytest.mark.asyncio
async def test_persist_vendor_scan_rejects_second_attribution_for_same_scan(db: Session) -> None:
    """A scan cannot be attributed to a second vendor (primary key scan_id constraint)."""
    scan = a_scan("test-scan-unique")
    db.add(scan)
    db.commit()

    submission_a = make_submission(vendor_id=uuid4())
    submission_b = make_submission(vendor_id=uuid4())

    await persist_vendor_scan(db, scan.id, submission_a)
    db.commit()

    await persist_vendor_scan(db, scan.id, submission_b)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


@pytest.mark.asyncio
async def test_get_vendor_jurisdiction_returns_matching_jurisdiction(db: Session) -> None:
    """get_vendor_jurisdiction reconstructs the full territorial jurisdiction."""
    scan = a_scan("test-scan-jur")
    db.add(scan)
    db.commit()

    vendor_id = uuid4()
    submission = make_submission(
        vendor_id=vendor_id,
        state="Maharashtra",
        region="Pune",
        district="Satara",
    )
    await persist_vendor_scan(db, scan.id, submission)
    db.commit()

    jurisdiction = await get_vendor_jurisdiction(db, submission.id)
    assert jurisdiction is not None
    assert isinstance(jurisdiction, Jurisdiction)
    assert jurisdiction.state == "Maharashtra"
    assert jurisdiction.region == "Pune"
    assert jurisdiction.district == "Satara"


@pytest.mark.asyncio
async def test_get_vendor_jurisdiction_with_state_only(db: Session) -> None:
    """get_vendor_jurisdiction handles nullable region and district correctly."""
    scan = a_scan("test-scan-state-only")
    db.add(scan)
    db.commit()

    vendor_id = uuid4()
    submission = make_submission(
        vendor_id=vendor_id,
        state="Telangana",
        region=None,
        district=None,
    )
    await persist_vendor_scan(db, scan.id, submission)
    db.commit()

    jurisdiction = await get_vendor_jurisdiction(db, submission.id)
    assert jurisdiction is not None
    assert jurisdiction.state == "Telangana"
    assert jurisdiction.region is None
    assert jurisdiction.district is None


@pytest.mark.asyncio
async def test_get_vendor_jurisdiction_absent_vendor_returns_none(db: Session) -> None:
    """Looking up jurisdiction for an unpersisted vendor returns None."""
    missing_id = uuid4()
    jurisdiction = await get_vendor_jurisdiction(db, missing_id)
    assert jurisdiction is None


@pytest.mark.asyncio
async def test_vendor_jurisdiction_integrates_with_route_verdict(db: Session) -> None:
    """Reconstructed vendor jurisdiction integrates directly with route_verdict."""
    scan = a_scan("test-scan-routing")
    db.add(scan)
    db.commit()

    # District-level vendor
    district_sub = make_submission(
        vendor_id=uuid4(),
        state="Maharashtra",
        region="Pune",
        district="Satara",
    )
    await persist_vendor_scan(db, scan.id, district_sub)
    db.commit()

    jur_district = await get_vendor_jurisdiction(db, district_sub.id)
    assert jur_district is not None

    decision_pass = route_verdict(jur_district, Verdict.PASS)
    assert decision_pass.target_tier == RoleTier.DISTRICT
    assert decision_pass.requires_visit is False
    assert decision_pass.action_required is False

    decision_viol = route_verdict(jur_district, Verdict.POTENTIAL_VIOLATION)
    assert decision_viol.target_tier == RoleTier.DISTRICT
    assert decision_viol.requires_visit is True
    assert decision_viol.action_required is True

    # State-level vendor (unpinned district and region)
    scan2 = a_scan("test-scan-routing-2")
    scan2.id = uuid4()
    db.add(scan2)
    db.commit()

    state_sub = make_submission(
        vendor_id=uuid4(),
        state="Maharashtra",
        region=None,
        district=None,
    )
    await persist_vendor_scan(db, scan2.id, state_sub)
    db.commit()

    jur_state = await get_vendor_jurisdiction(db, state_sub.id)
    assert jur_state is not None

    decision_state = route_verdict(jur_state, Verdict.POTENTIAL_VIOLATION)
    assert decision_state.target_tier == RoleTier.STATE
    assert decision_state.requires_visit is True


def test_repository_aliases_identity() -> None:
    """Convenience aliases reference the identical underlying functions."""
    assert record_vendor_scan is persist_vendor_scan
    assert persist_vendor_submission is persist_vendor_scan
    assert record_vendor_submission is persist_vendor_scan
    assert lookup_vendor_jurisdiction is get_vendor_jurisdiction


@pytest.mark.asyncio
async def test_caller_owns_commit_convention(db: Session) -> None:
    """Repository stages and flushes; changes are not durable until caller commits."""
    scan = a_scan("test-scan-commit")
    db.add(scan)
    db.commit()

    submission = make_submission(vendor_id=uuid4())
    await persist_vendor_scan(db, scan.id, submission)

    # Roll back before caller commit
    db.rollback()

    stored = db.get(VendorScanRow, scan.id)
    assert stored is None

    stored_vendor = db.get(VendorRow, submission.id)
    assert stored_vendor is None


@pytest.mark.asyncio
async def test_get_vendor_and_get_vendor_scan_helpers(db: Session) -> None:
    """get_vendor and get_vendor_scan retrieve records or return None."""
    scan = a_scan("test-scan-helpers")
    db.add(scan)
    db.commit()

    submission = make_submission(vendor_id=uuid4())
    await persist_vendor_scan(db, scan.id, submission)
    db.commit()

    vendor = await get_vendor(db, submission.id)
    assert vendor is not None
    assert vendor.name == submission.name

    vendor_scan = await get_vendor_scan(db, scan.id)
    assert vendor_scan is not None
    assert vendor_scan.scan_id == scan.id

    assert await get_vendor(db, uuid4()) is None
    assert await get_vendor_scan(db, uuid4()) is None
