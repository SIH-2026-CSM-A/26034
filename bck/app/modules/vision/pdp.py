import os
from dataclasses import dataclass

import cv2
import numpy as np

# Strictly prevent ultralytics from attempting online network downloads
os.environ["YOLO_OFFLINE"] = "1"
os.environ["ULTRALYTICS_OFFLINE"] = "1"


@dataclass(frozen=True)
class PDPResult:
    """Result of Principal Display Panel (PDP) detection."""

    bounding_box: tuple[int, int, int, int]
    area_cm2: float
    confidence: float
    cropped_image: np.ndarray


def detect_pdp(
    image: np.ndarray | str | os.PathLike,
    weights_path: str | None = None,
    confidence_threshold: float = 0.25,
    px_to_cm_ratio: float = 0.0264,
    model_path: str | None = None,
) -> PDPResult:
    """Detect Principal Display Panel (PDP) bounding box and area using YOLO detector.

    If PDP_WEIGHTS_PATH (weights_path/model_path) is missing, unset, or non-existent,
    gracefully executes the empty-detection fallback branch returning full-image bounds
    (0, 0, w, h) with confidence=0.0 without attempting network downloads or stock COCO
    weight fallbacks.
    """
    if isinstance(image, (str, os.PathLike)):
        img_path = str(image)
        if not os.path.isfile(img_path):
            raise ValueError(f"Input image file not found: {img_path}")

        loaded_img = cv2.imread(img_path)
        if loaded_img is None or loaded_img.size == 0:
            raise ValueError("Input image for PDP detection cannot be empty.")
        image = loaded_img

    if image is None or (isinstance(image, np.ndarray) and image.size == 0):
        raise ValueError("Input image for PDP detection cannot be empty.")

    h, w = image.shape[:2]

    # Resolve weights_path from model_path alias or env var if not set
    effective_weights_path = weights_path if weights_path is not None else model_path
    if effective_weights_path is None:
        effective_weights_path = os.getenv("PDP_WEIGHTS_PATH")

    # Handle missing, unset (empty/blank), or non-existent weights_path gracefully
    if (
        not effective_weights_path
        or not str(effective_weights_path).strip()
        or not os.path.isfile(str(effective_weights_path))
    ):
        area_cm2 = float((w * px_to_cm_ratio) * (h * px_to_cm_ratio))
        return PDPResult(
            bounding_box=(0, 0, w, h),
            area_cm2=round(area_cm2, 2),
            confidence=0.0,
            cropped_image=image.copy(),
        )

    from ultralytics import YOLO

    model = YOLO(effective_weights_path)
    results = model.predict(image, conf=confidence_threshold, verbose=False)

    if not results or len(results[0].boxes) == 0:
        area_cm2 = float((w * px_to_cm_ratio) * (h * px_to_cm_ratio))
        return PDPResult(
            bounding_box=(0, 0, w, h),
            area_cm2=round(area_cm2, 2),
            confidence=0.0,
            cropped_image=image.copy(),
        )

    best_box = max(results[0].boxes, key=lambda b: float(b.conf[0]))
    xyxy = best_box.xyxy[0].cpu().numpy().astype(int)
    x1, y1, x2, y2 = xyxy[0], xyxy[1], xyxy[2], xyxy[3]
    w_px = max(1, x2 - x1)
    h_px = max(1, y2 - y1)

    area_cm2 = float((w_px * px_to_cm_ratio) * (h_px * px_to_cm_ratio))
    cropped = image[y1:y2, x1:x2].copy()
    conf = float(best_box.conf[0])

    return PDPResult(
        bounding_box=(int(x1), int(y1), int(w_px), int(h_px)),
        area_cm2=round(area_cm2, 2),
        confidence=round(conf, 4),
        cropped_image=cropped,
    )
