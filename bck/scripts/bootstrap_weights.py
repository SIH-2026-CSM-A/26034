import shutil
from pathlib import Path

from paddleocr import PaddleOCR

print("Triggering native PaddleOCR download...")
# Calling without custom paths forces PaddleX to download the default models
PaddleOCR(lang="en", use_angle_cls=False, device="cpu")

paddlex_dir = Path.home() / ".paddlex" / "official_models"
det_src, rec_src = None, None

if paddlex_dir.exists():
    for yml in paddlex_dir.rglob("inference.yml"):
        name = yml.parent.name.lower()
        if "det" in name and not det_src:
            det_src = yml.parent
        if "rec" in name and not rec_src:
            rec_src = yml.parent

if det_src and rec_src:
    det_dst = Path.home() / ".cache" / "pccs" / "models" / "ocr_det"
    rec_dst = Path.home() / ".cache" / "pccs" / "models" / "ocr_rec"
    shutil.copytree(det_src, det_dst, dirs_exist_ok=True)
    shutil.copytree(rec_src, rec_dst, dirs_exist_ok=True)
    print("Offline cache successfully populated!")
else:
    print("Could not find downloaded inference.yml files.")
