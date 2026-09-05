from dataclasses import dataclass
from enum import StrEnum

import cv2
import numpy as np


class QualityReason(StrEnum):
    PASS = "PASS"
    BLUR_EXCESSIVE = "BLUR_EXCESSIVE"
    GLARE_EXCESSIVE = "GLARE_EXCESSIVE"
    INCOMPLETE = "INCOMPLETE"


# Intensity threshold (0-255) above which grayscale pixels are identified as glare.
GLARE_INTENSITY_THRESHOLD = 245
# Minimum contour area (in pixels) to consider a detected document/box candidate valid.
MIN_CONTOUR_AREA = 5000


@dataclass
class QualityResult:
    is_valid: bool
    reason_code: QualityReason
    blur_score: float
    glare_ratio: float
    coverage_ratio: float


def evaluate_quality(image: np.ndarray) -> QualityResult:
    """
    Evaluates image quality for downstream OCR and compliance processing.
    Returns a QualityResult with machine-readable reason codes (no legal verdicts).
    """
    if image is None or image.size == 0:
        return QualityResult(
            is_valid=False,
            reason_code=QualityReason.INCOMPLETE,
            blur_score=0.0,
            glare_ratio=0.0,
            coverage_ratio=0.0,
        )

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    # 1. Blur evaluation using Laplacian variance
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    is_blurry = blur_score < 100.0

    # 2. Glare evaluation
    glare_mask = gray >= GLARE_INTENSITY_THRESHOLD
    glare_ratio = float(np.sum(glare_mask)) / float(h * w)
    has_excessive_glare = glare_ratio > 0.15

    # 3. Completeness / Coverage evaluation
    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    max_area = 0.0
    for c in contours:
        area = cv2.contourArea(c)
        if area > max_area:
            max_area = area

    coverage_ratio = max_area / float(h * w)
    is_incomplete = coverage_ratio < 0.30

    # Determine reason code and validity
    if is_blurry:
        reason_code = QualityReason.BLUR_EXCESSIVE
        is_valid = False
    elif has_excessive_glare:
        reason_code = QualityReason.GLARE_EXCESSIVE
        is_valid = False
    elif is_incomplete:
        reason_code = QualityReason.INCOMPLETE
        is_valid = False
    else:
        reason_code = QualityReason.PASS
        is_valid = True

    return QualityResult(
        is_valid=is_valid,
        reason_code=reason_code,
        blur_score=blur_score,
        glare_ratio=glare_ratio,
        coverage_ratio=coverage_ratio,
    )


def remap_curvature(image: np.ndarray) -> np.ndarray:
    """
    Applies cylindrical unwarping to correct curvature distortion on cylindrical
    packaging. Assumes a cylindrical projection centered at the image midpoint
    with a radius equal to half the image width (w/2).
    """
    if image is None or image.size == 0:
        return image

    h, w = image.shape[:2]
    camera_matrix = np.array(
        [[w, 0, w / 2], [0, w, h / 2], [0, 0, 1]],
        dtype=np.float32,
    )
    dist_coeffs = np.zeros((4, 1), dtype=np.float32)

    map_x, map_y = cv2.initUndistortRectifyMap(
        camera_matrix,
        dist_coeffs,
        None,
        camera_matrix,
        (w, h),
        cv2.CV_32FC1,
    )
    return cv2.remap(image, map_x, map_y, cv2.INTER_LINEAR)


def remove_glare(image: np.ndarray) -> np.ndarray:
    """
    Removes specular glare using HSV thresholding and Fast-Marching inpainting.
    """
    if image is None or image.size == 0:
        return image

    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    _, s, v = cv2.split(hsv)

    # Glare is characterised by very high value (V >= 215) and low saturation (S <= 45)
    glare_mask = cv2.inpaint_mask = cv2.bitwise_and(
        cv2.compare(v, 215, cv2.CMP_GE),
        cv2.compare(s, 45, cv2.CMP_LE),
    )

    # Use Fast-Marching Method for inpainting specular spots
    return cv2.inpaint(image, glare_mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)


def correct_shadows(image: np.ndarray) -> np.ndarray:
    """
    Applies CLAHE strictly to the LAB L-channel, leaving A and B untouched
    to prevent brand color shifting.
    """
    if image is None or image.size == 0:
        return image

    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l_enhanced = clahe.apply(l_channel)

    lab_enhanced = cv2.merge([l_enhanced, a_channel, b_channel])
    return cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)
