import hashlib
import json

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


def compute_entry_hash(sequence: int, timestamp: str, payload_hash: str, prev_hash: str) -> str:
    """Computes the hash of an evidence entry metadata."""
    data = f"{sequence}:{timestamp}:{payload_hash}:{prev_hash}"
    return compute_sha256(data)


def create_genesis_entry(payload: dict | str, timestamp: str) -> EvidenceEntry:
    """Creates the first entry in the evidence chain."""
    sequence = 0
    prev_hash = GENESIS_PREV_HASH
    payload_hash = compute_payload_hash(payload)
    entry_hash = compute_entry_hash(sequence, timestamp, payload_hash, prev_hash)

    return EvidenceEntry(
        sequence=sequence,
        timestamp=timestamp,
        payload_hash=payload_hash,
        prev_hash=prev_hash,
        entry_hash=entry_hash,
        payload=payload,
    )


def append_entry(prev_entry: EvidenceEntry, payload: dict | str, timestamp: str) -> EvidenceEntry:
    """Appends a new entry to the evidence chain."""
    sequence = prev_entry.sequence + 1
    prev_hash = prev_entry.entry_hash
    payload_hash = compute_payload_hash(payload)
    entry_hash = compute_entry_hash(sequence, timestamp, payload_hash, prev_hash)

    return EvidenceEntry(
        sequence=sequence,
        timestamp=timestamp,
        payload_hash=payload_hash,
        prev_hash=prev_hash,
        entry_hash=entry_hash,
        payload=payload,
    )


def verify_chain(entries: list[EvidenceEntry]) -> ChainVerification:
    """Verifies the integrity and continuity of the evidence chain."""
    if not entries:
        return ChainVerification(is_valid=False, broken_link_index=0, reason="Chain is empty")

    for i, entry in enumerate(entries):
        # 1. Verify payload hash
        if entry.payload_hash != compute_payload_hash(entry.payload):
            return ChainVerification(
                is_valid=False, broken_link_index=i, reason="Payload hash mismatch"
            )

        # 2. Verify entry hash
        actual_entry_hash = compute_entry_hash(
            entry.sequence, entry.timestamp, entry.payload_hash, entry.prev_hash
        )
        if entry.entry_hash != actual_entry_hash:
            return ChainVerification(
                is_valid=False, broken_link_index=i, reason="Entry hash mismatch"
            )

        # 3. Verify sequence and continuity
        if i == 0:
            if entry.sequence != 0 or entry.prev_hash != GENESIS_PREV_HASH:
                return ChainVerification(
                    is_valid=False, broken_link_index=0, reason="Invalid genesis entry"
                )
        else:
            prev = entries[i - 1]
            if entry.prev_hash != prev.entry_hash:
                return ChainVerification(
                    is_valid=False, broken_link_index=i, reason="Chain link broken"
                )
            if entry.sequence != prev.sequence + 1:
                return ChainVerification(
                    is_valid=False, broken_link_index=i, reason="Sequence gap detected"
                )

    return ChainVerification(is_valid=True)
