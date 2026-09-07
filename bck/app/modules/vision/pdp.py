import os, numpy as np
from dataclasses import dataclass
from ultralytics import YOLO

@dataclass
class PDPResult:
    bbox: tuple
    confidence: float
    text: str = ""

def detect_pdp(image_path, weights_path=None) -> PDPResult:
    if isinstance(image_path, np.ndarray) and image_path.size == 0:
        raise ValueError("No PDP detected in image.")
    w = weights_path or os.getenv("PDP_WEIGHTS_PATH")
    if not w or not os.path.exists(w):
        raise RuntimeError("PDP_WEIGHTS_PATH is unset. Cannot execute PDP detection without calibrated weights.")
    
    res = YOLO(w)(image_path)
    if not res or not res[0].boxes or len(res[0].boxes) == 0:
        raise ValueError("No PDP detected in image.")
    
    c = res[0].boxes.xyxy[0].cpu().numpy()
    return PDPResult(
        bbox=(int(c[0]), int(c[1]), int(c[2]-c[0]), int(c[3]-c[1])),
        confidence=float(res[0].boxes.conf[0].cpu().numpy())
    )
