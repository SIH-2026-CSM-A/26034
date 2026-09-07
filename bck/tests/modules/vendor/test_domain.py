"""Unit tests for vendor domain models (VND-001 Part A).

Tests VendorType enum and VendorSubmission model validation, immutability,
and field constraints using constructed objects only.
"""

from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.core import Jurisdiction, VendorType
from app.modules.vendor.domain import VendorSubmission


def test_vendor_type_members():
    """VendorType enum defines GODOWN, SUPERMARKET, and KIRANA as lowercase strings."""
    assert VendorType.GODOWN == "godown"
    assert VendorType.SUPERMARKET == "supermarket"
    assert VendorType.KIRANA == "kirana"
    assert set(VendorType) == {
        VendorType.GODOWN,
        VendorType.SUPERMARKET,
        VendorType.KIRANA,
    }


def test_vendor_submission_creation():
    """VendorSubmission constructs successfully with all required fields."""
    vendor_id = uuid4()
    submission = VendorSubmission(
        id=vendor_id,
        name="Sri Krishna Stores",
        vendor_type=VendorType.KIRANA,
        jurisdiction=Jurisdiction(
            state="Karnataka",
            region="South",
            district="Bengaluru Urban",
        ),
        image_reference="uploads/vendors/2026/09/sample_label.jpg",
    )

    assert submission.id == vendor_id
    assert isinstance(submission.id, UUID)
    assert submission.name == "Sri Krishna Stores"
    assert submission.vendor_type == VendorType.KIRANA
    assert submission.image_reference == "uploads/vendors/2026/09/sample_label.jpg"
    assert submission.state == "Karnataka"
    assert submission.region == "South"
    assert submission.district == "Bengaluru Urban"

    # Verify convenience aliases
    assert submission.vendor_id == vendor_id
    assert submission.vendor_name == "Sri Krishna Stores"
    assert submission.image_ref == "uploads/vendors/2026/09/sample_label.jpg"


def test_vendor_submission_with_aliases():
    """VendorSubmission can be constructed using field aliases and UUID strings."""
    vendor_id = uuid4()
    submission = VendorSubmission(
        vendor_id=str(vendor_id),
        vendor_name="Mega Mart Supermarket",
        vendor_type=VendorType.SUPERMARKET,
        jurisdiction={"state": "Maharashtra", "district": "Mumbai"},
        image_ref="minio://scans/labels/megamart_01.png",
    )

    assert submission.id == vendor_id
    assert submission.vendor_id == vendor_id
    assert submission.name == "Mega Mart Supermarket"
    assert submission.vendor_type == VendorType.SUPERMARKET
    assert submission.image_reference == "minio://scans/labels/megamart_01.png"
    assert submission.state == "Maharashtra"
    assert submission.district == "Mumbai"
    assert submission.region is None


def test_vendor_submission_jurisdiction_optional_region_and_district():
    """Jurisdiction mirrors Scan shape: state is required, region and district are optional."""
    vendor_id = uuid4()
    state_only = VendorSubmission(
        id=vendor_id,
        name="Deccan Central Warehouse",
        vendor_type=VendorType.GODOWN,
        jurisdiction=Jurisdiction(state="Telangana"),
        image_reference="s3://vendor-images/deccan_01.png",
    )
    assert state_only.id == vendor_id
    assert state_only.state == "Telangana"
    assert state_only.region is None
    assert state_only.district is None


def test_vendor_submission_rejects_invalid_id_and_empty_strings():
    """VendorSubmission rejects invalid UUID for id, and empty strings for name/image_reference."""
    jur = Jurisdiction(state="Karnataka")

    with pytest.raises(ValidationError):
        VendorSubmission(
            id="",
            name="Valid Name",
            vendor_type=VendorType.KIRANA,
            jurisdiction=jur,
            image_reference="img.jpg",
        )

    with pytest.raises(ValidationError):
        VendorSubmission(
            id="not-a-valid-uuid",
            name="Valid Name",
            vendor_type=VendorType.KIRANA,
            jurisdiction=jur,
            image_reference="img.jpg",
        )

    with pytest.raises(ValidationError):
        VendorSubmission(
            id=uuid4(),
            name="",
            vendor_type=VendorType.KIRANA,
            jurisdiction=jur,
            image_reference="img.jpg",
        )

    with pytest.raises(ValidationError):
        VendorSubmission(
            id=uuid4(),
            name="Valid Name",
            vendor_type=VendorType.KIRANA,
            jurisdiction=jur,
            image_reference="",
        )


def test_vendor_submission_rejects_invalid_vendor_type():
    """VendorSubmission rejects invalid vendor_type values."""
    with pytest.raises(ValidationError):
        VendorSubmission(
            id=uuid4(),
            name="Store",
            vendor_type="ONLINE_STORE",  # Not in VendorType
            jurisdiction=Jurisdiction(state="Karnataka"),
            image_reference="img.jpg",
        )


def test_vendor_submission_frozen_immutability():
    """ContractModel enforces frozen=True; modifying attributes raises ValidationError."""
    submission = VendorSubmission(
        id=uuid4(),
        name="Store",
        vendor_type=VendorType.KIRANA,
        jurisdiction=Jurisdiction(state="Karnataka"),
        image_reference="img.jpg",
    )
    with pytest.raises(ValidationError):
        submission.name = "New Name"  # type: ignore[misc]


def test_vendor_submission_rejects_extra_fields():
    """ContractModel enforces extra='forbid'; unknown fields raise ValidationError."""
    with pytest.raises(ValidationError):
        VendorSubmission(
            id=uuid4(),
            name="Store",
            vendor_type=VendorType.KIRANA,
            jurisdiction=Jurisdiction(state="Karnataka"),
            image_reference="img.jpg",
            scan_id="00000000-0000-0000-0000-000000000000",  # extra field
        )


def test_vendor_submission_does_not_wrap_scan():
    """VendorSubmission carries submission-time vendor data only, not a scan model."""
    fields = set(VendorSubmission.model_fields.keys())
    assert "scan" not in fields
    assert "scan_id" not in fields
    assert "verdict" not in fields
    assert "findings" not in fields
    assert fields == {"id", "name", "vendor_type", "jurisdiction", "image_reference"}
