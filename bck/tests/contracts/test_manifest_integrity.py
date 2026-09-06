import json
import os


def test_manifest_annotation_hash_integrity():
    manifest_path = (
        "datasets/manifest.json"
        if os.path.exists("datasets/manifest.json")
        else "../datasets/manifest.json"
    )
    assert os.path.exists(manifest_path), f"manifest.json not found at {manifest_path}"

    with open(manifest_path) as f:
        manifest = json.load(f)

    for rec in manifest.get("records", []):
        ann_path = rec["annotation_path"]
        if not os.path.exists(ann_path):
            ann_path = os.path.join("..", rec["annotation_path"])

        assert os.path.exists(ann_path), f"Annotation missing for {rec['sample_id']}"

        with open(ann_path) as f:
            ann_data = json.load(f)

        assert ann_data.get("image_sha256") == rec["sha256"], (
            f"Hash mismatch in {rec['sample_id']}: annotation has {ann_data.get('image_sha256')}, "
            f"manifest has {rec['sha256']}"
        )

def test_annotation_image_sha256_matches_manifest():
    manifest_path = "../datasets/manifest.json" if os.path.exists("../datasets/manifest.json") else "datasets/manifest.json"
    with open(manifest_path) as f:
        manifest = json.load(f)

    for rec in manifest.get("records", []):
        ann_path = rec["annotation_path"]
        if not os.path.exists(ann_path) and os.path.exists(os.path.join("..", ann_path)):
            ann_path = os.path.join("..", ann_path)

        with open(ann_path) as f:
            ann_data = json.load(f)

        assert ann_data.get("image_sha256") == rec["sha256"], (
            f"Annotation {ann_path} image_sha256 ({ann_data.get('image_sha256')}) "
            f"does not match manifest sha256 ({rec['sha256']})"
        )
