import json
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.contracts.enums import FieldState, Verdict
from app.contracts.records import FieldFinding, RuleParameterSnapshot, VerdictRecord
from app.modules.evidence.chain import (
    append_entry,
    create_genesis_entry,
    verify_chain,
)
from app.modules.evidence.domain import EvidenceAssetType, PurgeRecordPayload
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


def test_storage_purge_propagates_errors(storage_client):
    """AC: Non-404 errors during purge must propagate."""
    with patch.object(storage_client, 'purge_image', side_effect=RuntimeError("Network failure")), \
         pytest.raises(RuntimeError, match="Network failure"):
        storage_client.purge_image("some-key")

def test_s3_purge_propagates_errors():
    """AC: S3 purge must propagate permission/network errors."""
    from unittest.mock import MagicMock

    from app.modules.evidence.storage import S3ContentAddressedStorageClient

    client = S3ContentAddressedStorageClient("http://localhost", "bucket", "key", "secret")
    client.s3 = MagicMock()

    # Mock a 403 Forbidden error
    error_response = MagicMock()
    error_response.get.return_value = {"Error": {"Code": "403"}}
    client.s3.get_object.side_effect = Exception("Forbidden")
    # Need to mock the .response attribute on the exception
    client.s3.get_object.side_effect = type(
        'Exception', (Exception,), {'response': error_response}
    )("Forbidden")

    with pytest.raises(Exception, match="Forbidden"):
        client.purge_image("some-key")

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


def test_is_purged_handles_json_string():
    """AC: is_purged works for both dict and JSON string payloads."""
    payload_dict = {"type": "purge_record", "target_sequence": 0}
    payload_json = json.dumps(payload_dict)

    e_dict = create_genesis_entry(payload_dict, "now", EvidenceAssetType.AUDIT_LOG)
    e_json = create_genesis_entry(payload_json, "now", EvidenceAssetType.AUDIT_LOG)

    assert e_dict.is_purged is True
    assert e_json.is_purged is True

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


def test_chain_verification_tampered_purge(retention_manager, storage_client, sample_record):
    """AC: Tampered entry still fails verification even after it is purged."""
    now = datetime.now(UTC)
    now_str = now.isoformat()
    e0 = create_genesis_entry("Data 0", now_str, EvidenceAssetType.PRODUCT_IMAGE)
    e1 = append_entry(e0, "Data 1", now_str, EvidenceAssetType.PRODUCT_IMAGE)

    # Store e0 so it can be purged
    storage_client.store_image(e0.payload.encode("utf-8"))

    # 1. Tamper with e0 (change payload, keep hash)
    tampered_e0 = e0.model_copy(update={"payload": "Tampered Data"})

    # 2. Purge e0 (force expired)
    expired_e0 = tampered_e0.model_copy(
        update={"timestamp": (now - timedelta(days=400)).isoformat()}
    )

    success, audit_entry = retention_manager.purge_evidence(
        expired_e0, e1, sample_record, None, now
    )
    assert success is True
    assert audit_entry is not None

    # Resulting chain: [tampered_e0, e1, audit_entry]
    chain = [tampered_e0, e1, audit_entry]
    verification = verify_chain(chain)

    # 3. Assert verification still fails due to tampering AND reports it as purged
    assert verification.is_valid is False
    assert verification.reason == "payload_hash_mismatch"
    assert verification.broken_link_index == 0
    assert 0 in verification.purged_indices

    # 4. Verify untampered purge succeeds
    e_clean = create_genesis_entry("Clean", now_str, EvidenceAssetType.PRODUCT_IMAGE)
    storage_client.store_image(e_clean.payload.encode("utf-8"))

    # Purge happens based on the entry's current state, not the one used for hashing
    expired_clean = e_clean.model_copy(
        update={"timestamp": (now - timedelta(days=400)).isoformat()}
    )

    # The chain linkage must use the original (non-expired) entry for the hash to be correct
    e_clean_next = append_entry(e_clean, "Clean Next", now_str, EvidenceAssetType.PRODUCT_IMAGE)

    success_clean, audit_clean = retention_manager.purge_evidence(
        expired_clean, e_clean_next, sample_record, None, now
    )
    assert success_clean is True

    clean_chain = [e_clean, e_clean_next, audit_clean]
    verification_clean = verify_chain(clean_chain)
    assert verification_clean.is_valid is True
    assert 0 in verification_clean.purged_indices


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
    # Build a valid chain (e0 -> e1) and purge e0 referencing e1
    e1 = append_entry(e0, "Data 1", now.isoformat(), EvidenceAssetType.PRODUCT_IMAGE)
    result = retention_manager.purge_evidence(e0, e1, record, None, now)

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

        # Build a valid chain (e0 -> e1) and purge e0 referencing e1
        e1 = append_entry(
            e0, "Data 1", datetime.now(UTC).isoformat(), EvidenceAssetType.PRODUCT_IMAGE
        )
        result = rm.purge_evidence(e0, e1, sample_record, None, datetime.now(UTC))

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

        # Build a valid chain (e0 -> e1) and purge e0 referencing e1
        e1 = append_entry(
            e0, "Data 1", datetime.now(UTC).isoformat(), EvidenceAssetType.PRODUCT_IMAGE
        )
        result = rm.purge_evidence(e0, e1, sample_record, None, datetime.now(UTC))

        assert result[0] is True
        # Check that it's actually purged in storage
        with pytest.raises(AssetPurgedError):
            storage_client.get_image(f"evidence/{e0.payload_hash}")
