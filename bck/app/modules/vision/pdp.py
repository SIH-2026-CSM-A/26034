import os
from dataclasses import dataclass

import numpy as np
from ultralytics import YOLO


@dataclass
class PDPResult:
    boxes: list[list]
    confidences: list[float]
    texts: list[str]


def detect_pdp(image_path: str | np.ndarray, weights_path: str | None = None) -> PDPResult:
    resolved_weights = weights_path or os.getenv("PDP_WEIGHTS_PATH")
    if not resolved_weights:
        raise RuntimeError(
            "PDP_WEIGHTS_PATH is unset. Cannot execute PDP detection without calibrated weights."
        )

    model = YOLO(resolved_weights)
    results = model(image_path)

    boxes = []
    confidences = []
    texts = []

    for r in results:
        if hasattr(r, "boxes") and r.boxes is not None and len(r.boxes) > 0:
            for box in r.boxes:
                coords = box.xyxy[0].cpu().numpy().tolist()
                conf = float(box.conf[0].cpu().numpy())
                boxes.append(coords)
                confidences.append(conf)
                texts.append("")

    if not boxes:
        raise ValueError("No PDP detected in image.")

    return PDPResult(boxes=boxes, confidences=confidences, texts=texts)
