import json
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.contracts import EvidenceAssetType


class EvidenceEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    sequence: int
    timestamp: str  # ISO-8601 UTC
    payload_hash: str  # SHA-256 hex digest
    prev_hash: str  # SHA-256 hex digest
    entry_hash: str  # SHA-256 hex digest
    payload: dict | str
    asset_type: EvidenceAssetType

    @property
    def is_purged(self) -> bool:
        """True if the payload is a purge record."""
        if isinstance(self.payload, dict):
            return self.payload.get("type") == "purge_record"
        if isinstance(self.payload, str):
            try:
                data = json.loads(self.payload)
                return isinstance(data, dict) and data.get("type") == "purge_record"
            except json.JSONDecodeError:
                return False
        return False

    @property
    def storage_key(self) -> str:
        """Derives the content-addressed storage key from the payload hash."""
        return f"evidence/{self.payload_hash}"


class PurgeRecordPayload(BaseModel):
    """Payload for an immutable purge event in the hash chain."""

    model_config = ConfigDict(frozen=True)

    type: str = "purge_record"
    target_sequence: int
    purge_timestamp: str
    reason: str


class ChainVerification(BaseModel):
    model_config = ConfigDict(frozen=True)

    is_valid: bool
    broken_link_index: int | None = None
    purged_indices: list[int] = []
    reason: (
        Literal[
            "payload_hash_mismatch",
            "previous_hash_mismatch",
            "ordering_violation",
            "entry_hash_mismatch",
            "missing_genesis",
            "corrupted_timestamp",
        ]
        | None
    ) = None
