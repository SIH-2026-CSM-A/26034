from unittest.mock import patch

from app.modules.evidence.chain import (
    GENESIS_PREV_HASH,
    append_entry,
    create_genesis_entry,
    verify_chain,
)
from app.modules.evidence.domain import ChainVerification
from app.modules.evidence.storage import ContentAddressedStorageClient
from app.modules.evidence.timestamp import LocalRFC3161Hook


def test_genesis_entry():
    """Verify create_genesis_entry produces sequence 0 and correct prev_hash."""
    payload = {"data": "genesis"}
    timestamp = "2026-09-05T12:00:00Z"
    entry = create_genesis_entry(payload, timestamp)

    assert entry.sequence == 0
    assert entry.prev_hash == GENESIS_PREV_HASH

    # Single genesis entry should be valid
    result = verify_chain([entry])
    assert isinstance(result, ChainVerification)
    assert result.is_valid is True


def test_long_chain_and_tampering():
    """Build a 100-entry chain, verify it, then tamper with it."""
    chain = []
    timestamp = "2026-09-05T12:00:00Z"

    # 1. Build 100-entry chain
    genesis = create_genesis_entry({"i": 0}, timestamp)
    chain.append(genesis)

    for i in range(1, 100):
        entry = append_entry(chain[-1], {"i": i}, timestamp)
        chain.append(entry)

    assert verify_chain(chain).is_valid is True

    # 2. Alter payload in entry index 42
    # Since EvidenceEntry is frozen, we must create a new one
    original_entry = chain[42]
    tampered_entry = original_entry.model_copy(update={"payload": {"i": "TAMPERED"}})

    tampered_chain = list(chain)
    tampered_chain[42] = tampered_entry

    result = verify_chain(tampered_chain)
    assert result.is_valid is False
    assert result.broken_link_index == 42


def test_entry_deletion():
    """Verify that deleting an entry breaks the chain at the gap."""
    chain = []
    timestamp = "2026-09-05T12:00:00Z"

    genesis = create_genesis_entry({"i": 0}, timestamp)
    chain.append(genesis)
    for i in range(1, 100):
        chain.append(append_entry(chain[-1], {"i": i}, timestamp))

    # Delete entry at index 15
    shortened_chain = list(chain)
    del shortened_chain[15]

    result = verify_chain(shortened_chain)
    assert result.is_valid is False
    assert result.broken_link_index == 15


def test_chain_continuity_reappend():
    """Verify appending to a valid chain maintains validity."""
    timestamp = "2026-09-05T12:00:00Z"
    chain = [create_genesis_entry({"i": 0}, timestamp)]

    # Verify initial
    assert verify_chain(chain).is_valid is True

    # Append and verify
    new_entry = append_entry(chain[-1], {"i": 1}, timestamp)
    chain.append(new_entry)

    assert verify_chain(chain).is_valid is True


def test_verify_chain_contract():
    """Assert return type is strictly ChainVerification."""
    timestamp = "2026-09-05T12:00:00Z"
    chain = [create_genesis_entry({"i": 0}, timestamp)]

    result = verify_chain(chain)
    assert type(result) is ChainVerification
    assert not isinstance(result, bool)


def test_content_addressed_storage():
    """Verify identical bytes result in same key and single store operation."""
    with (
        patch("pathlib.Path.write_bytes") as mock_write,
        patch("pathlib.Path.exists") as mock_exists,
    ):
        # First call to exists() returns False (file doesn't exist)
        # Second call to exists() returns True (file now exists)
        mock_exists.side_effect = [False, True]

        client = ContentAddressedStorageClient(base_path="test_storage")
        img_bytes = b"fake-image-data"

        key1 = client.store_image(img_bytes)
        key2 = client.store_image(img_bytes)

        assert key1 == key2
        # write_bytes should only be called once because the second exists() was True
        assert mock_write.call_count == 1


def test_isolation_no_network():
    """Assert no remote network calls occur during operation."""
    # We use a hook to ensure LocalRFC3161Hook doesn't try to hit a TSA
    hook = LocalRFC3161Hook()

    with patch("urllib.request.urlopen") as mock_url, patch("socket.socket") as mock_socket:
        token = hook.get_timestamp_token("some-hash")

        assert "timestamp" in token
        assert "token" in token

        mock_url.assert_not_called()
        mock_socket.assert_not_called()
