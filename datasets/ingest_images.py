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

def sync_manifest(drive_folder_id: str) -> Dict[str, Any]:
    if not drive_folder_id or "TODO" in drive_folder_id or "REPLACE" in drive_folder_id or drive_folder_id == "YOUR_ACTUAL_DRIVE_FOLDER_ID":
        raise ValueError("A valid Google Drive folder ID must be provided to sync the manifest.")

    samples = []

    if RAW_DIR.exists():
        for img_path in RAW_DIR.glob("**/*.[jJ][pP][gG]"):
            abs_path = img_path.resolve()
            rel_path = abs_path.relative_to(Path.cwd().resolve())
            sample_num = img_path.stem
            sku_name = img_path.parent.name
            category = img_path.parent.parent.name
            
            full_sku_id = f"{category}_{sku_name}"
            full_sample_id = f"{full_sku_id}_{sample_num}"
            
            anno_file_name = f"{full_sample_id}.json"
            anno_path = ANNOTATIONS_DIR / category / anno_file_name

            samples.append({
                "sample_id": full_sample_id,
                "sku_id": full_sku_id,
                "category": category,
                "relative_image_path": str(rel_path),
                "annotation_path": str(anno_path) if anno_path.exists() else None,
                "sha256": calculate_sha256(abs_path),
                "ingestion_status": "READY_FOR_ANNOTATION" if anno_path.exists() else "MISSING_ANNOTATION"
            })

    manifest = {
        "manifest_version": "1.0",
        "drive_folder_id": drive_folder_id,
        "total_samples": len(samples),
        "samples": samples
    }

    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"Manifest updated successfully at {MANIFEST_PATH} ({len(samples)} samples found).")
    return manifest

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Error: Missing required drive_folder_id argument.")
        print("Usage: python3 datasets/ingest_images.py <DRIVE_FOLDER_ID>")
        sys.exit(1)
    sync_manifest(sys.argv[1])
