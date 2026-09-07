import os
from dataclasses import dataclass

import numpy as np

# Strictly prevent ultralytics from attempting online network downloads
os.environ["YOLO_OFFLINE"] = "1"
os.environ["ULTRALYTICS_OFFLINE"] = "1"


@dataclass
class DetectionResult:
    """Result of Principal Display Panel (PDP) detection."""

    bbox: tuple[int, int, int, int]
    area: int
    confidence: float


def detect_pdp(
    image: np.ndarray,
    weights_path: str | None = None,
) -> DetectionResult:
    """Detects the Principal Display Panel using YOLO.

    Requires an explicit path to local weights or PDP_WEIGHTS_PATH environment variable.
    If weights_path is unset, missing, or empty, explicitly raises RuntimeError.
    """
    if image is None or image.size == 0:
        return DetectionResult((0, 0, 0, 0), 0, 0.0)

    if weights_path is None:
        weights_path = os.getenv("PDP_WEIGHTS_PATH")

    if not weights_path or not str(weights_path).strip() or not os.path.exists(weights_path):
        raise RuntimeError(
            "PDP_WEIGHTS_PATH is unset. Cannot execute PDP detection without calibrated weights."
        )

    from ultralytics import YOLO

    model = YOLO(weights_path)
    results = model(image, verbose=False)

    if not results or len(results[0].boxes) == 0:
        h, w = image.shape[:2]
        return DetectionResult((0, 0, w, h), w * h, 0.0)

    boxes = results[0].boxes
    best_idx = int(boxes.conf.argmax())
    x1, y1, x2, y2 = boxes.xyxy[best_idx].cpu().numpy()
    conf = float(boxes.conf[best_idx].cpu().numpy())

    x, y = int(x1), int(y1)
    w, h = int(x2 - x1), int(y2 - y1)

    return DetectionResult((x, y, w, h), w * h, conf)
