# Vision Module

**Owner:** @aksha08-ya

All computer vision lives in this module: panel OCR, PDP bounding box detection, blur/glare standard checks, deskewing, and cylindrical unrolling.

Layers live inside this package, not above it:

| File | Holds |
|---|---|
| `ocr.py` | PaddleOCR 3.7.0 panel text extraction, Tesseract MRP re-pass, and arbitration. |
| `pdp.py` | Principal Display Panel (PDP) bounding box and area detection via YOLO. |
| `preprocess.py` | Image quality gate (blur, glare, completeness), deskew, cylindrical remap, CLAHE. |
| `domain.py` | Data structures for vision results. |

## Imports

This module may import `app.contracts`, `app.core`, and itself. Nothing else.

Importing another module under `app.modules` — or anything under `app.pipeline` —
fails `lint-imports` in CI. If you need something another module has, the shared type
belongs in `app.contracts` and the composition belongs in `app.pipeline`.

---

## Offline Model Caching & Setup Protocol (VIS-004)

All model weights and tessdata dependencies must be cached locally prior to running the application. The system operates strictly offline without on-demand network downloads.

### 1. Model & Data Dependencies Summary

Total model storage footprint: **~25.8 MB**.

| Component | Model / Resource | Size | Target Cache Directory |
|---|---|---|---|
| PDP Detection | YOLOv8n custom fine-tuned weights (`pdp_yolov8n.pt`) | ~6.2 MB | `~/.cache/pccs/models/` |
| Text Detection | PaddleOCR 3.x detection model (`ch_PP-OCRv4_det_infer`) | ~4.7 MB | `~/.cache/pccs/models/ocr_det` |
| Text Recognition | PaddleOCR 3.x recognition model (`ch_PP-OCRv4_rec_infer`) | ~10.8 MB | `~/.cache/pccs/models/ocr_rec` |
| Tesseract OCR | English language traineddata (`eng.traineddata`) | ~4.1 MB | `/usr/share/tesseract-ocr/4.00/tessdata` |

### 2. Tesseract Installation & tessdata Setup

Install Tesseract OCR engine and English traineddata package:

```bash
sudo apt-get update && sudo apt-get install -y tesseract-ocr libtesseract-dev tesseract-ocr-eng
```

Export the tessdata directory environment variable:

```bash
export TESSERACT_TESSDATA_DIR=/usr/share/tesseract-ocr/4.00/tessdata
```

Required data file: `eng.traineddata` (~4.1 MB).

### 3. PaddleOCR 3.7.0 Models Caching

Download and extract PaddleOCR 3.x text detection (`ch_PP-OCRv4_det`) and recognition (`ch_PP-OCRv4_rec`) models for offline inference:

```bash
mkdir -p ~/.cache/pccs/models/ocr_det ~/.cache/pccs/models/ocr_rec

# Download Detection Model
wget https://paddleocr.bj.bcebos.com/PP-OCRv4/chinese/ch_PP-OCRv4_det_infer.tar -O det.tar
tar -xf det.tar -C ~/.cache/pccs/models/ocr_det --strip-components=1
rm det.tar

# Download Recognition Model
wget https://paddleocr.bj.bcebos.com/PP-OCRv4/chinese/ch_PP-OCRv4_rec_infer.tar -O rec.tar
tar -xf rec.tar -C ~/.cache/pccs/models/ocr_rec --strip-components=1
rm rec.tar
```

Alternatively, pre-cache via Python initialization:

```python
from paddleocr import PaddleOCR

ocr = PaddleOCR(
    text_detection_model_dir="~/.cache/pccs/models/ocr_det",
    text_recognition_model_dir="~/.cache/pccs/models/ocr_rec",
    use_textline_orientation=False,
    device="cpu",
)
```

### 4. Principal Display Panel (PDP) YOLO Weights Caching

Place the fine-tuned `pdp_yolov8n.pt` weights in the model cache:

```bash
mkdir -p ~/.cache/pccs/models
cp /path/to/pdp_yolov8n.pt ~/.cache/pccs/models/pdp_yolov8n.pt
```

Set environment variable:

```bash
export PDP_WEIGHTS_PATH=~/.cache/pccs/models/pdp_yolov8n.pt
```

If `PDP_WEIGHTS_PATH` is missing, unset, or set to an empty/blank string, `detect_pdp` gracefully executes the empty-detection fallback branch returning full-image bounds `(0, 0, w, h)` with `confidence=0.0` without attempting network downloads or stock COCO weight fallbacks.

### 5. Environment Variables Configuration

Copy `bck/.env.example` to `bck/.env` and ensure the vision model paths are set:

```ini
PDP_WEIGHTS_PATH=/home/user/.cache/pccs/models/pdp_yolov8n.pt
OCR_DET_MODEL_DIR=/home/user/.cache/pccs/models/ocr_det
OCR_REC_MODEL_DIR=/home/user/.cache/pccs/models/ocr_rec
TESSERACT_TESSDATA_DIR=/usr/share/tesseract-ocr/4.00/tessdata
```

Note: Blank values in environment variables are treated as unset.