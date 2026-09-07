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
        return isinstance(self.payload, dict) and self.payload.get("type") == "purge_record"


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
