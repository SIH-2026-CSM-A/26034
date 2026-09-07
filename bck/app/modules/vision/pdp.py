from dataclasses import dataclass


@dataclass
class PDPResult:
    boxes: list[list]
    confidences: list[float]
    texts: list[str]


def detect_pdp(image_path: str, weights_path: str | None = None) -> PDPResult:
    # Strict refusal on empty/missing detections
    # If no detection is found, raise ValueError explicitly
    boxes = []
    confidences = []
    texts = []

    if not boxes:
        raise ValueError("No PDP detected in image.")

    return PDPResult(boxes=boxes, confidences=confidences, texts=texts)
