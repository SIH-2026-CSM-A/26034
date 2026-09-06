from unittest.mock import patch

from app.modules.evidence.chain import (
    append_entry,
    compute_entry_hash,
    create_genesis_entry,
    verify_chain,
)
from app.modules.evidence.domain import EvidenceEntry


def build_valid_chain(length: int = 10):
    """Helper to build a valid evidence chain of specified length."""
    timestamp = "2026-09-06T10:00:00Z"
    entries = [create_genesis_entry({"i": 0}, timestamp)]
    for i in range(1, length):
        entries.append(append_entry(entries[-1], {"i": i}, timestamp))
    return entries


def test_genesis_only_chain():
    """Edge Case: Chain of exactly 1 entry (genesis only) is valid."""
    chain = build_valid_chain(1)
    result = verify_chain(chain)
    assert result.is_valid is True
    assert result.reason is None


def test_long_clean_chain():
    """Edge Case: Clean chain of 50+ entries is valid."""
    chain = build_valid_chain(60)
    result = verify_chain(chain)
    assert result.is_valid is True
    assert result.reason is None


def test_tamper_mutated_payload():
    """Tamper 1: Mutate payload at index 5 without updating payload_hash."""
    chain = build_valid_chain(10)
    # Mutate payload at index 5
    original_entry = chain[5]
    tampered_entry = original_entry.model_copy(update={"payload": {"i": "MUTATED"}})
    chain[5] = tampered_entry

    result = verify_chain(chain)
    assert result.is_valid is False
    assert result.broken_link_index == 5
    assert result.reason == "payload_hash_mismatch"


def test_tamper_swapped_entries():
    """Tamper 2: Swap entry 3 and entry 4."""
    chain = build_valid_chain(10)
    # Swap index 3 and 4
    chain[3], chain[4] = chain[4], chain[3]

    result = verify_chain(chain)
    assert result.is_valid is False
    assert result.broken_link_index == 3
    # Entry 4 (now at index 3) points to Entry 3 (now at index 4)
    # But it's preceded by Entry 2. prev_hash check fails first.
    assert result.reason == "previous_hash_mismatch"


def test_tamper_middle_entry_deleted():
    """Tamper 3: Remove entry 4 from a 10-entry chain."""
    chain = build_valid_chain(10)
    del chain[4]

    result = verify_chain(chain)
    assert result.is_valid is False
    assert result.broken_link_index == 4
    assert result.reason == "previous_hash_mismatch"


def test_tamper_foreign_entry_inserted():
    """Tamper 4: Insert a rogue entry at index 4."""
    chain = build_valid_chain(10)
    rogue = EvidenceEntry(
        sequence=99,
        timestamp="2026-09-06T10:00:00Z",
        payload_hash="rogue-hash",
        prev_hash="rogue-prev",
        entry_hash="rogue-entry",
        payload={"data": "rogue"},
    )
    # Make it internally consistent to avoid early hash failure
    from app.modules.evidence.chain import compute_payload_hash

    p_hash = compute_payload_hash(rogue.payload)
    e_hash = compute_entry_hash(rogue.sequence, rogue.timestamp, p_hash, rogue.prev_hash)
    rogue = rogue.model_copy(update={"payload_hash": p_hash, "entry_hash": e_hash})

    chain.insert(4, rogue)

    result = verify_chain(chain)
    assert result.is_valid is False
    assert result.broken_link_index == 4
    assert result.reason == "previous_hash_mismatch"


def test_tamper_recomputed_hash_attack():
    """Tamper 5: Mutate entry 5, recompute hashes, break link to entry 6."""
    chain = build_valid_chain(10)
    from app.modules.evidence.chain import compute_payload_hash

    # Mutate entry 5
    entry5 = chain[5]
    new_payload = {"i": "ATTACK"}
    new_p_hash = compute_payload_hash(new_payload)
    new_e_hash = compute_entry_hash(entry5.sequence, entry5.timestamp, new_p_hash, entry5.prev_hash)
    chain[5] = entry5.model_copy(
        update={"payload": new_payload, "payload_hash": new_p_hash, "entry_hash": new_e_hash}
    )

    # Entry 6's prev_hash still points to the OLD entry 5 hash.
    # Verification should fail at index 6.
    result = verify_chain(chain)
    assert result.is_valid is False
    assert result.broken_link_index == 6
    assert result.reason == "previous_hash_mismatch"


def test_offline_isolation():
    """Assert verify_chain completes successfully with zero network calls."""
    chain = build_valid_chain(5)

    with patch("socket.socket") as mock_socket:
        mock_socket.side_effect = Exception("Network access forbidden!")
        result = verify_chain(chain)
        assert result.is_valid is True
        mock_socket.assert_not_called()


def test_append_only_enforcement():
    """Verify no functions in the evidence module start with update_, edit_, modify_, or patch_."""
    import inspect

    import app.modules.evidence as evidence_mod

    forbidden_prefixes = ("update_", "edit_", "modify_", "patch_")
    public_members = inspect.getmembers(evidence_mod, predicate=inspect.isfunction)

    for name, _ in public_members:
        assert not name.startswith(forbidden_prefixes), f"Forbidden mutation function found: {name}"
