"""The demonstration seed's ward spread actually produces three density bands.

``scripts/seed_demo.py`` assigns each seeded scan a real GHMC ward so the jurisdiction
map is shaded from recorded locations rather than a hash. The point of the assignment is
that the map shows HIGH, MEDIUM and LOW — not one flat colour — so this replicates the
dashboard's own tercile band rule (``HeatmapJurisdiction.tsx``) and asserts all three
appear over the seed's own verdict pattern. If the weighting in ``_PV_BAG`` is flattened,
this goes red.

Not marked ``postgres``: ``assign_demo_wards`` is a pure function, so this needs no
database and no API. The seed script is imported by path because ``scripts`` is not a
package.
"""

import importlib.util
from collections import Counter
from pathlib import Path

_SEED = Path(__file__).resolve().parent.parent / "scripts" / "seed_demo.py"
_spec = importlib.util.spec_from_file_location("seed_demo_under_test", _SEED)
assert _spec and _spec.loader
seed_demo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(seed_demo)


def _bands(counts: list[int]) -> dict[int, str]:
    """The dashboard's band rule, transcribed from ``densityBands`` in
    ``HeatmapJurisdiction.tsx`` so this test fails if the seed and that rule disagree: the
    distinct counts are ranked into thirds by value."""
    distinct = sorted(set(counts))
    n = len(distinct)
    if n == 0:
        return {}
    if n == 1:
        only = distinct[0]
        return {only: "HIGH" if only > 10 else "MEDIUM" if only > 0 else "LOW"}
    if n == 2:
        return {distinct[0]: "LOW", distinct[1]: "HIGH"}
    cut = max(1, n // 3)
    out = {}
    for i, count in enumerate(distinct):
        out[count] = "LOW" if i < cut else "HIGH" if i >= n - cut else "MEDIUM"
    return out


def _pv_counts_per_ward(verdicts: list[str]) -> list[int]:
    """Potential-violation count for every ward that carries at least one scan — the
    exact input the map computes its bands over."""
    wards = seed_demo.assign_demo_wards(verdicts)
    totals: Counter[str] = Counter(wards)
    violations: Counter[str] = Counter(
        ward
        for ward, verdict in zip(wards, verdicts, strict=True)
        if verdict == "POTENTIAL_VIOLATION"
    )
    return [violations.get(ward, 0) for ward in totals]


def test_the_seed_spread_shows_all_three_density_bands() -> None:
    """Over the seed's own 30-scan verdict pattern, the wards span HIGH, MEDIUM and LOW."""
    verdicts = seed_demo._predicted_seed_verdicts(30)
    counts = _pv_counts_per_ward(verdicts)
    bands = _bands(counts)
    present = {bands[c] for c in counts}
    assert present == {"HIGH", "MEDIUM", "LOW"}, (present, counts)


def test_assignment_is_deterministic() -> None:
    """The same verdict list always yields the same wards, so a re-run of the backfill is
    idempotent rather than reshuffling the map."""
    verdicts = seed_demo._predicted_seed_verdicts(30)
    assert seed_demo.assign_demo_wards(verdicts) == seed_demo.assign_demo_wards(verdicts)


def test_only_potential_violations_land_in_the_gradient_wards() -> None:
    """A non-violation scan never lands in a gradient ward, so a ward's shade reflects its
    violations and not merely how many scans happened to be filed there."""
    verdicts = seed_demo._predicted_seed_verdicts(30)
    wards = seed_demo.assign_demo_wards(verdicts)
    for ward, verdict in zip(wards, verdicts, strict=True):
        if verdict != "POTENTIAL_VIOLATION":
            assert ward not in seed_demo.PV_GRADIENT_WARDS
