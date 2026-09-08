import hashlib
import json
from datetime import datetime

from app.contracts import EvidenceAssetType

from .domain import ChainVerification, EvidenceEntry

GENESIS_PREV_HASH = "0" * 64


def compute_sha256(data: bytes | str) -> str:
    """Computes the SHA-256 hash of the given data."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def compute_payload_hash(payload: dict | str) -> str:
    """Computes the SHA-256 hash of the payload using canonical JSON."""
    if isinstance(payload, dict):
        # Canonical JSON: sorted keys, no whitespace
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    else:
        serialized = str(payload)
    return compute_sha256(serialized)


def compute_entry_hash(
    sequence: int, timestamp: str, payload_hash: str, prev_hash: str, asset_type: EvidenceAssetType
) -> str:
    """Computes the hash of an evidence entry metadata.

    ``asset_type`` is inside the hash because it decides when the entry may be destroyed.
    Left outside, an entry could be relabelled from one asset class to another, fall under
    a different retention window, and :func:`verify_chain` would still report the chain
    intact — a tamper vector on the one structure whose purpose is detecting tampering.
    """
    asset_val = asset_type.value if hasattr(asset_type, "value") else str(asset_type)
    data = f"{sequence}:{timestamp}:{payload_hash}:{prev_hash}:{asset_val}"
    return compute_sha256(data)


def create_genesis_entry(
    payload: dict | str, timestamp: str, asset_type: EvidenceAssetType
) -> EvidenceEntry:
    """Creates the first entry in the evidence chain."""
    sequence = 0
    prev_hash = GENESIS_PREV_HASH
    payload_hash = compute_payload_hash(payload)
    entry_hash = compute_entry_hash(sequence, timestamp, payload_hash, prev_hash, asset_type)

    return EvidenceEntry(
        sequence=sequence,
        timestamp=timestamp,
        payload_hash=payload_hash,
        prev_hash=prev_hash,
        entry_hash=entry_hash,
        payload=payload,
        asset_type=asset_type,
    )


def append_entry(
    prev_entry: EvidenceEntry, payload: dict | str, timestamp: str, asset_type: EvidenceAssetType
) -> EvidenceEntry:
    """Appends a new entry to the evidence chain."""
    sequence = prev_entry.sequence + 1
    prev_hash = prev_entry.entry_hash
    payload_hash = compute_payload_hash(payload)
    entry_hash = compute_entry_hash(sequence, timestamp, payload_hash, prev_hash, asset_type)

    return EvidenceEntry(
        sequence=sequence,
        timestamp=timestamp,
        payload_hash=payload_hash,
        prev_hash=prev_hash,
        entry_hash=entry_hash,
        payload=payload,
        asset_type=asset_type,
    )


def append_purge_entry(
    prev_entry: EvidenceEntry, target_sequence: int, reason: str, timestamp: str
) -> EvidenceEntry:
    """Appends an immutable purge record to the evidence chain."""
    from .domain import PurgeRecordPayload

    payload = PurgeRecordPayload(
        target_sequence=target_sequence,
        purge_timestamp=timestamp,
        reason=reason,
    ).model_dump()

    # Purge records are AUDIT_LOG type
    from app.contracts import EvidenceAssetType

    return append_entry(
        prev_entry=prev_entry,
        payload=payload,
        timestamp=timestamp,
        asset_type=EvidenceAssetType.AUDIT_LOG,
    )


def verify_chain(entries: list[EvidenceEntry]) -> ChainVerification:
    """Verifies the integrity and continuity of the evidence chain."""
    if not entries:
        return ChainVerification(is_valid=False, broken_link_index=0, reason="missing_genesis")

    # 1. Identify purged entries first, as they may still be part of a tampered chain
    purged_indices = []
    for entry in entries:
        if entry.is_purged and isinstance(entry.payload, dict):
            target_seq = entry.payload.get("target_sequence")
            for idx, e in enumerate(entries):
                if e.sequence == target_seq:
                    purged_indices.append(idx)
                    break

    for i, entry in enumerate(entries):
        # Timestamp validation (Offline ISO-8601 UTC)
        try:
            datetime.fromisoformat(entry.timestamp.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return ChainVerification(
                is_valid=False,
                broken_link_index=i,
                reason="corrupted_timestamp",
                purged_indices=purged_indices,
            )

        # Payload integrity
        if entry.payload_hash != compute_payload_hash(entry.payload):
            return ChainVerification(
                is_valid=False,
                broken_link_index=i,
                reason="payload_hash_mismatch",
                purged_indices=purged_indices,
            )

        # Entry hash integrity
        actual_entry_hash = compute_entry_hash(
            entry.sequence, entry.timestamp, entry.payload_hash, entry.prev_hash, entry.asset_type
        )
        if entry.entry_hash != actual_entry_hash:
            return ChainVerification(
                is_valid=False,
                broken_link_index=i,
                reason="entry_hash_mismatch",
                purged_indices=purged_indices,
            )

        # Chain linkage and sequence
        if i == 0 and (entry.sequence != 0 or entry.prev_hash != GENESIS_PREV_HASH):
            return ChainVerification(
                is_valid=False,
                broken_link_index=0,
                reason="missing_genesis",
                purged_indices=purged_indices,
            )
        if i == 0:
            continue

        prev = entries[i - 1]
        # Hash linkage
        if entry.prev_hash != prev.entry_hash:
            return ChainVerification(
                is_valid=False,
                broken_link_index=i,
                reason="previous_hash_mismatch",
                purged_indices=purged_indices,
            )
        # Sequence ordering
        if entry.sequence != prev.sequence + 1:
            return ChainVerification(
                is_valid=False,
                broken_link_index=i,
                reason="ordering_violation",
                purged_indices=purged_indices,
            )

    return ChainVerification(is_valid=True, purged_indices=sorted(list(set(purged_indices))))
