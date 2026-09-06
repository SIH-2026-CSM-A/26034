from unittest.mock import MagicMock, patch

import pytest

from app.modules.evidence.chain import (
    GENESIS_PREV_HASH,
    append_entry,
    create_genesis_entry,
    verify_chain,
)
from app.modules.evidence.domain import ChainVerification
from app.modules.evidence.storage import LocalStorageClient, S3ContentAddressedStorageClient
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
        mock_exists.side_effect = [False, True]

        client = LocalStorageClient(base_path="test_storage")
        img_bytes = b"fake-image-data"

        key1 = client.store_image(img_bytes)
        key2 = client.store_image(img_bytes)

        assert key1 == key2
        assert mock_write.call_count == 1


def test_storage_path_handling(tmp_path):
    """Verify custom base_path writes to custom_storage/evidence/..."""
    custom_path = tmp_path / "custom_storage"
    client = LocalStorageClient(base_path=str(custom_path))
    img_bytes = b"test-bytes"

    key = client.store_image(img_bytes)

    # Verify file exists at the expected location
    expected_file = custom_path / key
    assert expected_file.exists()
    assert expected_file.read_bytes() == img_bytes


def test_s3_storage_mocked():
    """Verify S3 client content-addressing and zero remote calls using mocks."""
    with patch("app.modules.evidence.storage.boto3", create=True) as mock_boto_mod:
        mock_s3 = MagicMock()
        mock_boto_mod.client.return_value = mock_s3

        client = S3ContentAddressedStorageClient(
            endpoint_url="http://localhost:9000",
            bucket_name="test-bucket",
            access_key="minioadmin",
            secret_key="minioadmin",
        )

        img_bytes = b"s3-fake-data"

        # Mock S3 to return 404 for the first call, then 200
        error_response = {"Error": {"Code": "404", "Message": "Not Found"}}

        class MockClientError(Exception):
            def __init__(self, response, operation):
                self.response = response
                self.operation = operation

        mock_s3.head_object.side_effect = MockClientError(error_response, "HeadObject")

        key = client.store_image(img_bytes)

        assert "evidence/" in key
        mock_s3.put_object.assert_called_once()
        assert mock_s3.put_object.call_args[1]["Key"] == key
        assert mock_s3.put_object.call_args[1]["Body"] == img_bytes


def test_timestamp_secret_validation():
    """Verify LocalRFC3161Hook raises ValueError if secret is missing or empty."""
    with pytest.raises(ValueError, match="secret_key is required"):
        LocalRFC3161Hook(secret_key="")

    with pytest.raises(TypeError):
        LocalRFC3161Hook()


def test_isolation_no_network():
    """Assert no remote network calls occur during operation."""
    hook = LocalRFC3161Hook(secret_key="test-secret")

    with patch("urllib.request.urlopen") as mock_url, patch("socket.socket") as mock_socket:
        token = hook.get_timestamp_token("some-hash")

        assert "timestamp" in token
        assert "token" in token

        mock_url.assert_not_called()
        mock_socket.assert_not_called()
