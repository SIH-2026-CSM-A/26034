import os

# Disable MKLDNN and new PIR executor to prevent C++ oneDNN crashes on CPU
os.environ["FLAGS_USE_MKLDNN"] = "0"
os.environ["FLAGS_ENABLE_PIR_API"] = "0"

from pathlib import Path

import cv2
from paddleocr import PaddleOCR


def run_proof() -> None:
    root_dir = Path(__file__).resolve().parent.parent.parent
    sample_path = root_dir / "datasets" / "raw" / "_staging" / "sample_capture.jpg"
    if not sample_path.exists():
        raise FileNotFoundError(f"Missing {sample_path}")

    det_dir = os.getenv(
        "OCR_DET_MODEL_DIR",
        str(Path.home() / ".cache" / "pccs" / "models" / "ocr_det"),
    )
    rec_dir = os.getenv(
        "OCR_REC_MODEL_DIR",
        str(Path.home() / ".cache" / "pccs" / "models" / "ocr_rec"),
    )
    if not os.path.isdir(det_dir):
        raise FileNotFoundError(f"Missing {det_dir}")
    if not os.path.isdir(rec_dir):
        raise FileNotFoundError(f"Missing {rec_dir}")

    print("=== VIS-004 PaddleOCR Proof Execution ===")
    print(f"Sample Image Path: {sample_path}")
    print(f"Resolved Text Detection Model: {det_dir}")
    print(f"Resolved Text Recognition Model: {rec_dir}")

    image = cv2.imread(str(sample_path))
    if image is None:
        raise ValueError("Failed to load image")

    # Explicitly disable mkldnn in kwargs as well for safety
    ocr = PaddleOCR(
        text_detection_model_dir=det_dir,
        text_recognition_model_dir=rec_dir,
        use_textline_orientation=False,
        device="cpu",
        enable_mkldnn=False,
    )
    results = ocr.predict(image)

    dt_polys_count = 0
    items = results if isinstance(results, list) else [results]
    rec_entries = []

    for item in items:
        if isinstance(item, dict) and "dt_polys" in item:
            polys = item.get("dt_polys", [])
            texts = item.get("rec_texts", [])
            scores = item.get("rec_scores", [])
            dt_polys_count += len(polys)
            for text, score in zip(texts, scores, strict=False):
                rec_entries.append((str(text), float(score)))

    print(f"\nTotal dt_polys count: {dt_polys_count}")
    print("First 5 rec_texts with rec_scores:")
    for idx, (text, score) in enumerate(rec_entries[:5], start=1):
        print(f"  {idx}. '{text}' (score: {score:.4f})")


if __name__ == "__main__":
    run_proof()
