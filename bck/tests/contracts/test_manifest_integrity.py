"""The manifest is the only link between a checked-in annotation and the image it describes.

DAT-007. Both tests here previously looped ``manifest["records"]`` with no assertion outside
the loop, so an empty or wholly-unresolvable manifest passed in 0.76 seconds having compared
nothing. They were green while all twelve records pointed at images that do not exist, which
is how DAT-005 (#77) merged claiming a corpus that was never on disk.

The repo root is resolved from this file's location, not from the working directory. The
previous ``..`` fallback meant a wrong cwd was indistinguishable from a passing corpus.
"""

import hashlib
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST = REPO_ROOT / "datasets" / "manifest.json"


def _records() -> list[dict]:
    assert MANIFEST.is_file(), f"manifest.json not found at {MANIFEST}"
    records = json.loads(MANIFEST.read_text()).get("records", [])
    assert records, (
        "datasets/manifest.json holds no records. An empty manifest is not a passing "
        "corpus — it is a corpus that cannot be verified, and every guard in this file "
        "would otherwise pass vacuously over it."
    )
    return records


def test_every_manifest_record_names_an_image_that_exists():
    """The guard DAT-005 needed and did not have.

    Twelve records named twelve images, none of which were on disk, and nothing failed.
    """
    missing = [
        r["relative_image_path"]
        for r in _records()
        if not (REPO_ROOT / r["relative_image_path"]).is_file()
    ]
    assert not missing, (
        f"{len(missing)} of {len(_records())} manifest records name an image that does not "
        f"exist on disk: {missing[:5]}"
    )


def test_every_manifest_record_names_an_annotation_that_exists():
    missing = [
        r["annotation_path"] for r in _records() if not (REPO_ROOT / r["annotation_path"]).is_file()
    ]
    assert not missing, f"{len(missing)} records name a missing annotation: {missing[:5]}"


def test_annotation_hash_matches_the_manifest():
    checked = 0
    for rec in _records():
        ann = REPO_ROOT / rec["annotation_path"]
        if not ann.is_file():
            pytest.fail(f"annotation missing for {rec['sample_id']} — see the guard above")
        data = json.loads(ann.read_text())
        assert data.get("image_sha256") == rec["sha256"], (
            f"{rec['sample_id']}: annotation says {data.get('image_sha256')}, "
            f"manifest says {rec['sha256']}"
        )
        checked += 1
    assert checked == len(_records()), "not every record was compared"


def test_the_manifest_hash_is_the_hash_of_the_image_on_disk():
    """The claim nothing has ever checked: that the recorded sha256 is the file's sha256.

    Matching the annotation against the manifest proves only that two documents agree.
    Neither has ever been compared to the bytes they describe.
    """
    checked = 0
    for rec in _records():
        img = REPO_ROOT / rec["relative_image_path"]
        if not img.is_file():
            pytest.fail(f"image missing for {rec['sample_id']} — see the guard above")
        actual = hashlib.sha256(img.read_bytes()).hexdigest()
        assert actual == rec["sha256"], (
            f"{rec['sample_id']}: file hashes to {actual}, manifest says {rec['sha256']}"
        )
        checked += 1
    assert checked == len(_records()), "not every record was hashed"
