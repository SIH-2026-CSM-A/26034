import os
from dataclasses import dataclass

import numpy as np


@dataclass
class DetectionResult:
    bbox: tuple[int, int, int, int]
    area: int
    confidence: float


def detect_pdp(image: np.ndarray, weights_path: str) -> DetectionResult:
    """
    Detects the Principal Display Panel using YOLO.
    Requires an explicit path to local weights to enforce offline capability.
    """
    if image is None or image.size == 0:
        return DetectionResult((0, 0, 0, 0), 0, 0.0)

    # Strictly prevent YOLO from attempting a network download if the file is missing
    if not os.path.exists(weights_path):
        raise FileNotFoundError(f"Offline model weights not found at: {weights_path}")

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
