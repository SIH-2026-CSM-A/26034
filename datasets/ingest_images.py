import json
import hashlib
from pathlib import Path
from typing import Dict, Any

MANIFEST_PATH = Path("datasets/manifest.json")
RAW_DIR = Path("datasets/raw")
ANNOTATIONS_DIR = Path("datasets/annotations")

def calculate_sha256(filepath: Path) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def sync_manifest(drive_folder_id: str = "TODO_INSERT_DRIVE_ID") -> Dict[str, Any]:
    samples = []

    if RAW_DIR.exists():
        for img_path in RAW_DIR.glob("**/*.[jJ][pP][gG]"):
            rel_path = img_path.relative_to(Path.cwd())
            sample_id = img_path.stem
            category = img_path.parent.parent.name
            anno_path = ANNOTATIONS_DIR / category / f"{sample_id}.json"

            samples.append({
                "sample_id": sample_id,
                "sku_id": img_path.parent.name,
                "category": category,
                "relative_image_path": str(rel_path),
                "annotation_path": str(anno_path) if anno_path.exists() else None,
                "sha256": calculate_sha256(img_path),
                "ingestion_status": "READY_FOR_ANNOTATION" if anno_path.exists() else "MISSING_ANNOTATION"
            })

    manifest = {
        "manifest_version": "1.0",
        "updated_at": "2026-09-05T21:09:55Z",
        "drive_folder_id": drive_folder_id,
        "total_samples": len(samples),
        "samples": samples
    }

    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"Manifest updated successfully at {MANIFEST_PATH} ({len(samples)} samples found).")
    return manifest

if __name__ == "__main__":
    sync_manifest()
