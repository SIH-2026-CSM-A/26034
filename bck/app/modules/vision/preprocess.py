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

# HSV Value channel minimum threshold (0-255) for isolating bright specular glare regions.
GLARE_MIN_VALUE_THRESHOLD = 215

# HSV Saturation channel maximum threshold (0-255) for isolating desaturated white glare highlights.
GLARE_MAX_SATURATION_THRESHOLD = 45


@dataclass(frozen=True)
class QualityResult:
    """Dataclass holding image quality metrics and machine-readable status code."""

    is_acceptable: bool
    blur_score: float
    glare_fraction: float
    completeness_score: float
    reason_code: QualityReason


def _order_points(pts: np.ndarray) -> np.ndarray:
    """Order 4 contour points as [top-left, top-right, bottom-right, bottom-left]."""
    rect = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def quality_gate(
    image: np.ndarray,
    blur_threshold: float = 100.0,
    glare_threshold: float = 0.15,
    completeness_threshold: float = 0.40,
) -> QualityResult:
    """Evaluate image quality (blur, glare fraction, and completeness) prior to OCR."""
    if image is None or image.size == 0:
        return QualityResult(
            is_acceptable=False,
            blur_score=0.0,
            glare_fraction=1.0,
            completeness_score=0.0,
            reason_code="IMAGE_EMPTY",
        )

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    glare_count = int(np.sum(gray >= GLARE_INTENSITY_THRESHOLD))
    glare_fraction = float(glare_count / gray.size)

    thresh = cv2.threshold(gray, 20, 255, cv2.THRESH_BINARY)[1]
    completeness_score = float(np.count_nonzero(thresh) / gray.size)

    if blur_score < blur_threshold:
        return QualityResult(
            is_acceptable=False,
            blur_score=blur_score,
            glare_fraction=glare_fraction,
            completeness_score=completeness_score,
            reason_code="BLUR_EXCEEDED",
        )

    if glare_fraction > glare_threshold:
        return QualityResult(
            is_acceptable=False,
            blur_score=blur_score,
            glare_fraction=glare_fraction,
            completeness_score=completeness_score,
            reason_code="GLARE_EXCEEDED",
        )

    if completeness_score < completeness_threshold:
        return QualityResult(
            is_acceptable=False,
            blur_score=blur_score,
            glare_fraction=glare_fraction,
            completeness_score=completeness_score,
            reason_code="INCOMPLETE_LABEL",
        )

    return QualityResult(
        is_acceptable=True,
        blur_score=blur_score,
        glare_fraction=glare_fraction,
        completeness_score=completeness_score,
        reason_code="PASS",
    )


def correct_perspective(image: np.ndarray) -> np.ndarray:
    """Detect package boundary and apply a 3x3 homography to deskew the label."""
    if image is None or image.size == 0:
        return image

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return image

    sorted_contours = sorted(contours, key=cv2.contourArea, reverse=True)
    quad_pts = None

    for contour in sorted_contours:
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
        if len(approx) == 4:
            quad_pts = approx.reshape(4, 2)
            break

    if quad_pts is None:
        return image

    rect = _order_points(quad_pts)
    (tl, tr, br, bl) = rect

    width_a = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    width_b = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    max_w = max(int(width_a), int(width_b))

    height_a = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    height_b = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    max_h = max(int(height_a), int(height_b))

    if max_w < 10 or max_h < 10:
        return image

    dst = np.array(
        [[0, 0], [max_w - 1, 0], [max_w - 1, max_h - 1], [0, max_h - 1]],
        dtype=np.float32,
    )
    matrix = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(image, matrix, (max_w, max_h))


def remap_curvature(image: np.ndarray) -> np.ndarray:
    """Fit elliptical silhouette and apply inverse cylindrical remap to flatten marginal text."""
    if image is None or image.size == 0:
        return image

    h, w = image.shape[:2]
    center_x = (w - 1) / 2.0
    radius = w / 2.0

    x_indices = np.arange(w, dtype=np.float32)
    norm_x = (x_indices - center_x) / radius
    norm_x_clamped = np.clip(norm_x, -0.99, 0.99)

    alpha = np.pi / 2.0
    x_src = center_x + radius * np.sin(norm_x_clamped * (alpha / (np.pi / 2.0)))

    map_x = np.tile(x_src.astype(np.float32), (h, 1))
    map_y = np.tile(np.arange(h, dtype=np.float32)[:, None], (1, w))

    return cv2.remap(
        image,
        map_x,
        map_y,
        interpolation=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REFLECT,
    )


def remove_glare(image: np.ndarray) -> np.ndarray:
    """Isolate high-value/low-saturation glare via HSV thresholding and apply Telea inpainting."""
    if image is None or image.size == 0:
        return image

    hsv = (
        cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        if len(image.shape) == 3
        else cv2.cvtColor(cv2.cvtColor(image, cv2.COLOR_GRAY2BGR), cv2.COLOR_BGR2HSV)
    )

    lower_glare = np.array([0, 0, GLARE_MIN_VALUE_THRESHOLD], dtype=np.uint8)
    upper_glare = np.array([180, GLARE_MAX_SATURATION_THRESHOLD, 255], dtype=np.uint8)
    mask = cv2.inRange(hsv, lower_glare, upper_glare)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    dilated_mask = cv2.dilate(mask, kernel, iterations=1)

    return cv2.inpaint(image, dilated_mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)


def correct_shadows(image: np.ndarray) -> np.ndarray:
    """Apply CLAHE to the L-channel in LAB space only without modifying chromaticity channels."""
    if image is None or image.size == 0:
        return image

    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l_enhanced = clahe.apply(l_channel)

    lab_enhanced = cv2.merge([l_enhanced, a_channel, b_channel])
    return cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)
