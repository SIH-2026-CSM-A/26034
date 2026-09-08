import hashlib
from abc import ABC, abstractmethod
from pathlib import Path

import boto3


class AssetPurgedError(Exception):
    """Raised when an asset has been purged for retention/privacy."""

    pass


class EvidenceStorageClient(ABC):
    """Abstract base class for evidence storage."""

    @abstractmethod
    def store_image(self, image_bytes: bytes) -> str:
        """
        Stores image bytes and returns a content-addressed storage key.
        """
        pass

    @abstractmethod
    def get_image(self, storage_key: str) -> bytes:
        """
        Retrieves image bytes by its storage key.
        """
        pass

    @abstractmethod
    def purge_image(self, storage_key: str) -> bool:
        """
        Permanently deletes the asset bytes and replaces them with a tombstone.
        Must be idempotent.

        Returns True if the object existed and was deleted, False if not found.
        """
        pass


class LocalStorageClient(EvidenceStorageClient):
    """
    Content-addressed storage for evidence files using the local filesystem.
    """

    def __init__(self, base_path: str = "storage"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def store_image(self, image_bytes: bytes) -> str:
        sha256_hash = hashlib.sha256(image_bytes).hexdigest()
        storage_key = f"evidence/{sha256_hash}"

        file_path = self.base_path / storage_key
        file_path.parent.mkdir(parents=True, exist_ok=True)

        if not file_path.exists():
            file_path.write_bytes(image_bytes)

        return storage_key

    def get_image(self, storage_key: str) -> bytes:
        file_path = self.base_path / storage_key
        if not file_path.exists():
            raise FileNotFoundError(f"Object not found: {storage_key}")

        data = file_path.read_bytes()
        if data == b"TOMBSTONE":
            raise AssetPurgedError(f"Asset purged: {storage_key}")

        return data

    def purge_image(self, storage_key: str) -> bool:
        file_path = self.base_path / storage_key
        if not file_path.exists():
            return False  # Not found

        if file_path.read_bytes() == b"TOMBSTONE":
            return True  # Idempotent: already purged, but existed

        file_path.write_bytes(b"TOMBSTONE")
        return True


class S3ContentAddressedStorageClient(EvidenceStorageClient):
    """
    Content-addressed storage for evidence files using MinIO/S3.
    """

    def __init__(
        self,
        endpoint_url: str,
        bucket_name: str,
        access_key: str,
        secret_key: str,
    ):
        self.s3 = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )
        self.bucket_name = bucket_name

    def store_image(self, image_bytes: bytes) -> str:
        sha256_hash = hashlib.sha256(image_bytes).hexdigest()
        storage_key = f"evidence/{sha256_hash}"

        try:
            # Deduplication: check if object exists before writing
            self.s3.head_object(Bucket=self.bucket_name, Key=storage_key)
        except Exception as e:
            # Use generic exception if botocore.exceptions.ClientError isn't available
            # or check for the specific 404 code in the response
            error_code = getattr(e, "response", {}).get("Error", {}).get("Code")
            if error_code == "404":
                # Object does not exist, upload it
                self.s3.put_object(
                    Bucket=self.bucket_name,
                    Key=storage_key,
                    Body=image_bytes,
                    ContentType="image/jpeg",
                )
            else:
                raise

        return storage_key

    def get_image(self, storage_key: str) -> bytes:
        response = self.s3.get_object(Bucket=self.bucket_name, Key=storage_key)
        data = response["Body"].read()
        if data == b"TOMBSTONE":
            raise AssetPurgedError(f"Asset purged: {storage_key}")
        return data

    def purge_image(self, storage_key: str) -> bool:
        try:
            from botocore.exceptions import ClientError

            response = self.s3.get_object(Bucket=self.bucket_name, Key=storage_key)
            if response["Body"].read() == b"TOMBSTONE":
                return True  # Idempotent
        except ClientError as e:
            # Check for 404 / NoSuchKey specifically
            error_code = e.response.get("Error", {}).get("Code")
            if error_code in ("404", "NoSuchKey"):
                return False
            raise
        except Exception:
            # For non-client errors, we can't be sure if it's a 404, but usually
            # we should not swallow these unless they are clearly 404s.
            # Re-raise to let the caller handle system failures.
            raise

        self.s3.put_object(
            Bucket=self.bucket_name,
            Key=storage_key,
            Body=b"TOMBSTONE",
            ContentType="text/plain",
        )
        return True
