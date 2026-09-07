from dataclasses import dataclass
from enum import StrEnum

import cv2
import numpy as np


class QualityReason(StrEnum):
    PASS = "PASS"
    BLUR_EXCEEDED = "BLUR_EXCEEDED"
    GLARE_EXCEEDED = "GLARE_EXCEEDED"
    IMAGE_EMPTY = "IMAGE_EMPTY"
    INCOMPLETE_LABEL = "INCOMPLETE_LABEL"


# Intensity threshold (0-255) above which grayscale pixels are identified as glare.
GLARE_INTENSITY_THRESHOLD = 245
# Intensity at or above which a pixel is treated as background rather than package surface.
# Uncalibrated prior: chosen so a white studio backdrop is excluded from the glare ratio.
# Glare is a reflection ON the package; a bright background is not glare. Measured on four
# real captures before this constant existed, the whole-frame ratio rejected 4/4, including
# one at 0.19 against a 0.15 threshold.
BACKGROUND_INTENSITY_THRESHOLD = 250
# Minimum contour area (in pixels) to consider a detected document/box candidate valid.
MIN_CONTOUR_AREA = 5000


@dataclass
class QualityResult:
    is_valid: bool
    reason_code: QualityReason
    blur_score: float
    glare_ratio: float
    coverage_ratio: float

    @property
    def is_acceptable(self) -> bool:
        return self.is_valid


def evaluate_quality(
    image: np.ndarray,
    blur_threshold: float = 100.0,
    glare_threshold: float = 0.30,
    completeness_threshold: float = 0.30,
) -> QualityResult:
    """
    Evaluates image quality for downstream OCR and compliance processing.
    Returns a QualityResult with machine-readable QualityReason enum members.

    ``glare_threshold`` is an UNCALIBRATED PRIOR. It was 0.15 against a whole-frame ratio
    that measured the studio backdrop rather than the package, and it refused 4/4 real
    captures. Measured over the package surface (VIS-010), four real captures span
    0.012-0.267 on glossy substrates, so 0.30 admits them. n=4. No accuracy or
    false-positive figure follows from this, and none may be quoted until a real corpus
    exists (DAT-007).
    """
    if image is None or image.size == 0:
        return QualityResult(
            is_valid=False,
            reason_code=QualityReason.IMAGE_EMPTY,
            blur_score=0.0,
            glare_ratio=0.0,
            coverage_ratio=0.0,
        )

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    # 1. Blur evaluation using Laplacian variance
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    is_blurry = blur_score < blur_threshold

    # 2. Glare evaluation, measured over the package surface rather than the whole frame.
    # A white backdrop is near-saturated everywhere, so a whole-frame ratio measures the
    # background, not the reflection.
    # The subject is the largest non-background contour: the package. A brightness cut
    # cannot serve here, because a specular highlight is itself near-white and would be
    # excluded from the very mask meant to catch it.
    _, subject_thresh = cv2.threshold(
        gray, BACKGROUND_INTENSITY_THRESHOLD, 255, cv2.THRESH_BINARY_INV
    )
    subject_contours, _ = cv2.findContours(
        subject_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    subject_region = np.zeros_like(gray)
    if subject_contours:
        largest = max(subject_contours, key=cv2.contourArea)
        cv2.drawContours(subject_region, [largest], -1, 255, thickness=cv2.FILLED)
    subject_px = float(np.count_nonzero(subject_region))
    if subject_px > 0:
        glare_mask = (subject_region > 0) & (gray >= GLARE_INTENSITY_THRESHOLD)
        glare_ratio = float(np.sum(glare_mask)) / subject_px
    else:
        # No package surface at all. Not a glare finding; the coverage check owns it.
        glare_ratio = 0.0
    has_excessive_glare = glare_ratio > glare_threshold

    # 3. Completeness / Coverage evaluation
    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    max_area = 0.0
    for c in contours:
        area = cv2.contourArea(c)
        if area > max_area:
            max_area = area

    coverage_ratio = max_area / float(h * w)
    is_incomplete = coverage_ratio < completeness_threshold

    # Determine reason code and validity using QualityReason members
    if is_blurry:
        reason_code = QualityReason.BLUR_EXCEEDED
        is_valid = False
    elif has_excessive_glare:
        reason_code = QualityReason.GLARE_EXCEEDED
        is_valid = False
    elif is_incomplete:
        reason_code = QualityReason.INCOMPLETE_LABEL
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


def quality_gate(
    image: np.ndarray,
    blur_threshold: float = 100.0,
    glare_threshold: float = 0.30,
    completeness_threshold: float = 0.30,
) -> QualityResult:
    """
    Alias for evaluate_quality accepting test parameters.
    """
    return evaluate_quality(
        image,
        blur_threshold=blur_threshold,
        glare_threshold=glare_threshold,
        completeness_threshold=completeness_threshold,
    )


def remap_curvature(image: np.ndarray) -> np.ndarray:
    """
    Applies cylindrical unwarping to correct curvature distortion on cylindrical
    packaging. Uses an explicit cylindrical surface projection mapping grid
    to flatten horizontally curved labels.
    """
    if image is None or image.size == 0:
        return image

    h, w = image.shape[:2]
    cx = w / 2.0
    radius = w * 0.8

    x_indices = np.arange(w, dtype=np.float32)
    val = np.clip((x_indices - cx) / radius, -1.0, 1.0)
    x_src = cx + radius * np.sin(val)

    map_x = np.tile(x_src.astype(np.float32), (h, 1))
    map_y = np.tile(np.arange(h, dtype=np.float32)[:, None], (1, w))

    return cv2.remap(image, map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def remove_glare(image: np.ndarray) -> np.ndarray:
    """
    Removes specular glare using HSV thresholding and Fast-Marching inpainting.
    """
    if image is None or image.size == 0:
        return image

    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    _, s, v = cv2.split(hsv)

    glare_mask = cv2.bitwise_and(
        cv2.compare(v, 215, cv2.CMP_GE),
        cv2.compare(s, 45, cv2.CMP_LE),
    )

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


def correct_perspective(image: np.ndarray) -> np.ndarray:
    """
    Detects document/label contours and applies perspective transformation (deskewing)
    using cv2.warpPerspective based on the detected 4-point quad contour.
    """
    if image is None or image.size == 0:
        return image

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 75, 200)

    contours, _ = cv2.findContours(edged.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]

    screen_cnt = None
    for c in contours:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4:
            screen_cnt = approx
            break

    if screen_cnt is None:
        return image

    pts = screen_cnt.reshape(4, 2).astype(np.float32)

    # Order points: top-left, top-right, bottom-right, bottom-left
    rect = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]

    tl, tr, br, bl = rect

    width_a = np.sqrt((br[0] - bl[0]) ** 2 + (br[1] - bl[1]) ** 2)
    width_b = np.sqrt((tr[0] - tl[0]) ** 2 + (tr[1] - tl[1]) ** 2)
    max_width = max(int(width_a), int(width_b))

    height_a = np.sqrt((tr[0] - br[0]) ** 2 + (tr[1] - br[1]) ** 2)
    height_b = np.sqrt((tl[0] - bl[0]) ** 2 + (tl[1] - bl[1]) ** 2)
    max_height = max(int(height_a), int(height_b))

    if max_width <= 0 or max_height <= 0:
        return image

    dst = np.array(
        [
            [0, 0],
            [max_width - 1, 0],
            [max_width - 1, max_height - 1],
            [0, max_height - 1],
        ],
        dtype=np.float32,
    )

    m_matrix = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(image, m_matrix, (max_width, max_height))
