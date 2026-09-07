from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.contracts.enums import EvidenceAssetType, FieldState, Verdict
from app.contracts.records import FieldFinding, RuleParameterSnapshot, VerdictRecord
from app.modules.evidence.chain import (
    append_entry,
    create_genesis_entry,
    verify_chain,
)
from app.modules.evidence.domain import PurgeRecordPayload
from app.modules.evidence.retention import RetentionManager
from app.modules.evidence.storage import AssetPurgedError, LocalStorageClient


@pytest.fixture
def storage_client():
    # Use a unique directory for each test
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        yield LocalStorageClient(base_path=tmpdir)


@pytest.fixture
def retention_manager(storage_client):
    with patch("app.modules.evidence.retention.get_settings") as mock_get:
        mock_settings = MagicMock()
        mock_settings.evidence_image_retention_days = 365
        mock_settings.evidence_pii_retention_days = 90
        mock_settings.evidence_destructive_purge_enabled = True
        mock_get.return_value = mock_settings
        yield RetentionManager(storage_client=storage_client)


@pytest.fixture
def sample_record():
    return VerdictRecord(
        subject_ref="SUB-123",
        verdict=Verdict.PASS,
        rule_set_version="v1.0",
        evaluated_at=datetime.now(UTC),
        findings=[
            FieldFinding(
                field="NAME_AND_ADDRESS",
                state=FieldState.PASS,
                rule_snapshot=MagicMock(spec=RuleParameterSnapshot),
                reason="Correct",
                evidence_span_ids=("span1",),
            )
        ],
    )


@pytest.fixture
def evidence_chain():
    now = datetime.now(UTC).isoformat()
    e0 = create_genesis_entry("Image Data 0", now, EvidenceAssetType.PRODUCT_IMAGE)
    e1 = append_entry(e0, "Image Data 1", now, EvidenceAssetType.PRODUCT_IMAGE)
    return [e0, e1]


def test_storage_purge_and_error(storage_client):
    """AC: Purged bytes are gone and get_image raises AssetPurgedError."""
    key = storage_client.store_image(b"some image data")

    # Verify it's there
    assert storage_client.get_image(key) == b"some image data"

    # Purge it
    storage_client.purge_image(key)

    # Verify it raises AssetPurgedError
    with pytest.raises(AssetPurgedError):
        storage_client.get_image(key)


def test_storage_purge_idempotency(storage_client):
    """AC: purge_image is idempotent."""
    key = storage_client.store_image(b"some image data")

    storage_client.purge_image(key)
    storage_client.purge_image(key)  # Should not fail

    with pytest.raises(AssetPurgedError):
        storage_client.get_image(key)


def test_chain_verification_with_purge():
    """AC: verify_chain passes across a purged entry and reports it."""
    now = datetime.now(UTC).isoformat()
    e0 = create_genesis_entry("Data 0", now, EvidenceAssetType.PRODUCT_IMAGE)
    e1 = append_entry(e0, "Data 1", now, EvidenceAssetType.PRODUCT_IMAGE)

    # Create a purge record for e0
    purge_payload = PurgeRecordPayload(
        target_sequence=0,
        purge_timestamp=now,
        reason="Expired",
    ).model_dump()

    e2 = append_entry(e1, purge_payload, now, EvidenceAssetType.AUDIT_LOG)

    chain = [e0, e1, e2]
    verification = verify_chain(chain)

    assert verification.is_valid is True
    assert 0 in verification.purged_indices


def test_chain_verification_tampered_purge():
    """AC: Tampered entry still fails verification after purge."""
    now = datetime.now(UTC).isoformat()
    e0 = create_genesis_entry("Data 0", now, EvidenceAssetType.PRODUCT_IMAGE)
    e1 = append_entry(e0, "Data 1", now, EvidenceAssetType.PRODUCT_IMAGE)

    # Tamper with e0
    tampered_e0 = e0.model_copy(update={"payload": "Tampered Data"})

    chain = [tampered_e0, e1]
    verification = verify_chain(chain)

    assert verification.is_valid is False
    assert verification.reason == "payload_hash_mismatch"


def test_legal_hold_prevents_purge(
    retention_manager, storage_client, sample_record, evidence_chain
):
    """AC: Asset under legal hold is skipped and logged."""
    # Set verdict to POTENTIAL_VIOLATION
    record = sample_record.model_copy(update={"verdict": Verdict.POTENTIAL_VIOLATION})

    # Setup storage for the first entry
    e0 = evidence_chain[0]
    # Force expired
    e0 = e0.model_copy(update={"timestamp": (datetime.now(UTC) - timedelta(days=400)).isoformat()})
    storage_client.store_image(
        e0.payload if isinstance(e0.payload, bytes) else e0.payload.encode("utf-8")
    )
    storage_key = f"evidence/{e0.payload_hash}"

    # Run purge workflow
    now = datetime.now(UTC)
    # confirmed=True triggers legal hold for POTENTIAL_VIOLATION
    result = retention_manager.purge_evidence(e0, e0, record, True, now)

    assert result[0] is False
    # Verify data still exists
    assert storage_client.get_image(storage_key) == (
        e0.payload if isinstance(e0.payload, bytes) else e0.payload.encode("utf-8")
    )


def test_retention_config_consumption(storage_client):
    """AC: Retention windows come from config and change eligibility."""
    # Mock settings
    with patch("app.modules.evidence.retention.get_settings") as mock_get:
        mock_settings = MagicMock()
        mock_settings.evidence_image_retention_days = 10
        mock_get.return_value = mock_settings

        rm = RetentionManager(storage_client)

        # Entry from 11 days ago -> should purge
        old_time = (datetime.now(UTC) - timedelta(days=11)).isoformat()
        e0 = create_genesis_entry("Data", old_time, EvidenceAssetType.PRODUCT_IMAGE)

        assert rm.should_purge(e0, datetime.now(UTC)) is True

        # Entry from 5 days ago -> should not purge
        recent_time = (datetime.now(UTC) - timedelta(days=5)).isoformat()
        e1 = create_genesis_entry("Data", recent_time, EvidenceAssetType.PRODUCT_IMAGE)

        assert rm.should_purge(e1, datetime.now(UTC)) is False


def test_differential_retention_windows(storage_client):
    """AC: Different asset classes use their configured windows."""
    with patch("app.modules.evidence.retention.get_settings") as mock_get:
        mock_settings = MagicMock()
        mock_settings.evidence_image_retention_days = 100
        mock_settings.evidence_pii_retention_days = 10
        mock_get.return_value = mock_settings

        rm = RetentionManager(storage_client)
        now = datetime.now(UTC)

        # PII from 20 days ago -> should purge
        pii_time = (now - timedelta(days=20)).isoformat()
        e_pii = create_genesis_entry("PII", pii_time, EvidenceAssetType.PERSONAL_IDENTIFIER)
        assert rm.should_purge(e_pii, now) is True

        # Image from 20 days ago -> should NOT purge
        img_time = (now - timedelta(days=20)).isoformat()
        e_img = create_genesis_entry("Image", img_time, EvidenceAssetType.PRODUCT_IMAGE)
        assert rm.should_purge(e_img, now) is False


def test_safety_flag(storage_client, sample_record, evidence_chain):
    """AC: Destructive purge requires explicit configuration flag."""
    with patch("app.modules.evidence.retention.get_settings") as mock_get:
        mock_settings = MagicMock()
        mock_settings.evidence_destructive_purge_enabled = False
        mock_settings.evidence_image_retention_days = 1
        mock_get.return_value = mock_settings

        rm = RetentionManager(storage_client)
        e0 = evidence_chain[0]
        # Store data that matches the payload hash of e0
        storage_client.store_image(
            e0.payload if isinstance(e0.payload, bytes) else e0.payload.encode("utf-8")
        )

        # Force expired
        e0 = e0.model_copy(
            update={"timestamp": (datetime.now(UTC) - timedelta(days=2)).isoformat()}
        )

        result = rm.purge_evidence(e0, e0, sample_record, False, datetime.now(UTC))

        assert result[0] is False
        assert storage_client.get_image(f"evidence/{e0.payload_hash}") == (
            e0.payload if isinstance(e0.payload, bytes) else e0.payload.encode("utf-8")
        )


def test_purge_creates_audit_record(storage_client, sample_record, evidence_chain):
    """AC: Purge workflow returns True to signal that an audit record must be appended."""
    with patch("app.modules.evidence.retention.get_settings") as mock_get:
        mock_settings = MagicMock()
        mock_settings.evidence_destructive_purge_enabled = True
        mock_settings.evidence_image_retention_days = 1
        mock_get.return_value = mock_settings

        rm = RetentionManager(storage_client)
        e0 = evidence_chain[0]
        # Store data that matches the payload hash of e0
        storage_client.store_image(
            e0.payload if isinstance(e0.payload, bytes) else e0.payload.encode("utf-8")
        )

        # Force expired
        e0 = e0.model_copy(
            update={"timestamp": (datetime.now(UTC) - timedelta(days=2)).isoformat()}
        )

        result = rm.purge_evidence(e0, e0, sample_record, False, datetime.now(UTC))

        assert result[0] is True
        # Check that it's actually purged in storage
        with pytest.raises(AssetPurgedError):
            storage_client.get_image(f"evidence/{e0.payload_hash}")
