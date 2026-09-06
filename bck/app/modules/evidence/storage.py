import hashlib
from pathlib import Path


class ContentAddressedStorageClient:
    """
    Content-addressed storage for evidence files.
    Uses a local filesystem abstraction to mimic S3/MinIO behavior.
    """

    def __init__(self, base_path: str = "storage/evidence"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def store_image(self, image_bytes: bytes) -> str:
        """
        Stores image bytes and returns a content-addressed storage key.
        Identical bytes result in the same key.
        """
        sha256_hash = hashlib.sha256(image_bytes).hexdigest()
        storage_key = f"evidence/{sha256_hash}"

        # Map storage key to local path
        file_path = self.base_path.parent / storage_key
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Store if not already present (content-addressed)
        if not file_path.exists():
            file_path.write_bytes(image_bytes)

        return storage_key

    def get_image(self, storage_key: str) -> bytes:
        """
        Retrieves image bytes by its storage key.
        """
        file_path = self.base_path.parent / storage_key
        if not file_path.exists():
            raise FileNotFoundError(f"Object not found: {storage_key}")

        return file_path.read_bytes()
