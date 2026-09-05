from pydantic import BaseModel, ConfigDict


class EvidenceEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    sequence: int
    timestamp: str  # ISO-8601 UTC
    payload_hash: str  # SHA-256 hex digest
    prev_hash: str  # SHA-256 hex digest
    entry_hash: str  # SHA-256 hex digest
    payload: dict | str


class ChainVerification(BaseModel):
    model_config = ConfigDict(frozen=True)

    is_valid: bool
    broken_link_index: int | None = None
    reason: str | None = None
