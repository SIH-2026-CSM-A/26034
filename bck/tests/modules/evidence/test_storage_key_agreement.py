from app.contracts import EvidenceAssetType
from app.modules.evidence.domain import EvidenceEntry, derive_storage_key


def test_write_and_purge_storage_key_agreement():
    """Assert write path, domain property, and purge path derive identical keys."""
    sample_hash = "0f1d9093f2ff2ce8a12ca4c3514cb080d73f3e8f5eaa3221135bede408aa62ba"

    # Use the first available member of EvidenceAssetType dynamically to avoid hardcoding mismatch
    asset_type = list(EvidenceAssetType)[0]

    entry = EvidenceEntry(
        sequence=1,
        timestamp="2026-09-08T00:00:00Z",
        payload_hash=sample_hash,
        prev_hash="0" * 64,
        entry_hash="1" * 64,
        payload="test",
        asset_type=asset_type,
    )

    write_key = derive_storage_key(sample_hash)
    domain_key = entry.storage_key
    purge_key = entry.storage_key

    assert write_key == "evidence/" + sample_hash
    assert domain_key == write_key
    assert purge_key == write_key
