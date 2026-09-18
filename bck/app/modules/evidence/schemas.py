"""What the evidence surface returns."""

from pydantic import BaseModel, ConfigDict

from app.contracts import EvidenceAssetType

from .domain import ChainVerification


class EntrySummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    sequence: int
    timestamp: str
    entry_hash: str
    asset_type: EvidenceAssetType
    is_purged: bool


class EvidenceView(BaseModel):
    """A scan's chain, verified on the way out.

    ``verification`` is computed on every read and never stored: a stored "valid" flag is
    the one thing an attacker who could edit an entry could also edit.
    """

    model_config = ConfigDict(frozen=True)

    scan_id: str
    verification: ChainVerification
    entries: list[EntrySummary]
