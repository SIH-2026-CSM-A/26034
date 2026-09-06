import hashlib
import urllib.request
from unittest.mock import MagicMock, patch

import boto3
import pytest

from app.modules.evidence.storage import S3ContentAddressedStorageClient

# Standard local MinIO connection parameters
MINIO_ENDPOINT = "http://localhost:9000"
MINIO_ACCESS_KEY = "minioadmin"
MINIO_SECRET_KEY = "minioadmin"
MINIO_BUCKET = "evidence"


def is_minio_reachable():
    """Checks if MinIO is reachable at the configured endpoint."""
    try:
        # Try to hit the health check endpoint
        with urllib.request.urlopen(f"{MINIO_ENDPOINT}/minio/health/live", timeout=2) as response:
            return response.getcode() == 200
    except Exception:
        return False


@pytest.fixture(scope="module")
def s3_client():
    """Provides a connected S3ContentAddressedStorageClient and ensures bucket exists."""
    client = S3ContentAddressedStorageClient(
        endpoint_url=MINIO_ENDPOINT,
        bucket_name=MINIO_BUCKET,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
    )

    # Ensure bucket exists
    s3_raw = boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
    )

    try:
        s3_raw.head_bucket(Bucket=MINIO_BUCKET)
    except Exception:
        s3_raw.create_bucket(Bucket=MINIO_BUCKET)

    return client


@pytest.mark.skipif(
    not is_minio_reachable(),
    reason="Live MinIO container not running in current environment",
)
def test_minio_roundtrip(s3_client):
    """Test storing and retrieving an image from real MinIO."""
    sample_bytes = b"minio-integration-test-data-12345"
    sha256_hash = hashlib.sha256(sample_bytes).hexdigest()
    expected_key = f"evidence/{sha256_hash}"

    # Store
    key = s3_client.store_image(sample_bytes)
    assert key == expected_key

    # Retrieve
    retrieved_bytes = s3_client.get_image(key)
    assert retrieved_bytes == sample_bytes


@pytest.mark.skipif(
    not is_minio_reachable(),
    reason="Live MinIO container not running in current environment",
)
def test_minio_deduplication(s3_client):
    """Verify that storing the same bytes twice does not create duplicate objects."""
    sample_bytes = b"dedup-test-data-67890"
    sha256_hash = hashlib.sha256(sample_bytes).hexdigest()
    expected_key = f"evidence/{sha256_hash}"

    # First store
    key1 = s3_client.store_image(sample_bytes)
    assert key1 == expected_key

    # Second store (identical bytes)
    key2 = s3_client.store_image(sample_bytes)
    assert key2 == expected_key
    assert key1 == key2


def test_s3_storage_mocked():
    """Verify S3 client content-addressing and zero remote calls using mocks."""
    with patch("app.modules.evidence.storage.boto3", create=True) as mock_boto_mod:
        mock_s3 = MagicMock()
        mock_boto_mod.client.return_value = mock_s3

        client = S3ContentAddressedStorageClient(
            endpoint_url=MINIO_ENDPOINT,
            bucket_name=MINIO_BUCKET,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
        )

        img_bytes = b"s3-mock-data"

        # Mock S3 to return 404 for the first call, then 200
        class MockClientError(Exception):
            def __init__(self, response, operation):
                self.response = response
                self.operation = operation

        error_response = {"Error": {"Code": "404", "Message": "Not Found"}}
        mock_s3.head_object.side_effect = MockClientError(error_response, "HeadObject")

        key = client.store_image(img_bytes)

        assert "evidence/" in key
        mock_s3.put_object.assert_called_once()
        assert mock_s3.put_object.call_args[1]["Key"] == key
        assert mock_s3.put_object.call_args[1]["Body"] == img_bytes
