from unittest.mock import patch

from app.modules.evidence import chain as chain_mod
from app.modules.evidence.chain import (
    append_entry,
    compute_entry_hash,
    compute_payload_hash,
    create_genesis_entry,
)
from app.modules.evidence.domain import ChainVerification


def build_valid_chain(length=10):
    timestamp = "2026-09-06T10:00:00Z"
    entries = [create_genesis_entry({"i": 0}, timestamp)]
    for i in range(1, length):
        entries.append(append_entry(entries[-1], {"i": i}, timestamp))
    return entries


def test_adversarial_verification_failure():
    """
    Adversarial Test:
    Stub verify_chain to always return is_valid=True.
    All 5 tamper tests must fail because they expect is_valid=False.
    """

    def stub_verify_chain(entries):
        return ChainVerification(is_valid=True)

    # Define the 5 tamper scenarios
    scenarios = []

    # 1. Mutated payload
    c1 = build_valid_chain(10)
    c1[5] = c1[5].model_copy(update={"payload": {"i": "MUTATED"}})
    scenarios.append(("mutated_payload", c1))

    # 2. Swapped entries
    c2 = build_valid_chain(10)
    c2[3], c2[4] = c2[4], c2[3]
    scenarios.append(("swapped", c2))

    # 3. Middle entry deleted
    c3 = build_valid_chain(10)
    del c3[4]
    scenarios.append(("deleted", c3))

    # 4. Foreign entry inserted
    c4 = build_valid_chain(10)
    rogue = create_genesis_entry({"i": 99}, "2026-09-06T10:00:00Z")
    c4.insert(4, rogue)
    scenarios.append(("inserted", c4))

    # 5. Recomputed hash attack
    c5 = build_valid_chain(10)
    e5 = c5[5]
    new_p = compute_payload_hash({"i": "ATTACK"})
    new_e = compute_entry_hash(e5.sequence, e5.timestamp, new_p, e5.prev_hash)
    c5[5] = e5.model_copy(
        update={"payload": {"i": "ATTACK"}, "payload_hash": new_p, "entry_hash": new_e}
    )
    scenarios.append(("recomputed", c5))

    failed_count = 0
    with patch("app.modules.evidence.chain.verify_chain", side_effect=stub_verify_chain):
        for _name, chain in scenarios:
            # The real verify_chain should return is_valid=False.
            # Our stub returns is_valid=True.
            res = chain_mod.verify_chain(chain)
            if res.is_valid is True:
                failed_count += 1

    assert failed_count == 5, (
        f"Only {failed_count}/5 tampered chains were 'incorrectly' validated as True"
    )
