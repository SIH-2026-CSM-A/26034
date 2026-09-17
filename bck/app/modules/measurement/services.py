import cv2
import numpy as np

from app.contracts import (
    MeasurementCalibrated,
    MeasurementExact,
    MeasurementMarginCalibrated,
    MeasurementMarginExact,
    MeasurementMarginOverlapCalibrated,
    MeasurementMarginOverlapExact,
    MeasurementRefusal,
    MeasurementResult,
)

from .schemas import MeasurementMarginSet, PackageShape

# If a measurement has zero variance (e.g. flush margins), we cannot claim perfect
# physical certainty. We document an uncalibrated prior based on pixel quantisation:
# the minimum uncertainty is exactly one pixel at the measured scale.
UNCALIBRATED_QUANTISATION_PRIOR_PX = 1.0
# Reference object physical dimensions
REF_DIMS = {
    "id_card": {"width_mm": 85.60, "height_mm": 53.98},
    "coin_10": {"diameter_mm": 27.0},
    "ean_13": {"width_mm": 37.29},
}

# Uncalibrated priors to be recalibrated once an evaluation set exists.
PRIOR_CONFIDENCE_CARD = 0.01
PRIOR_CONFIDENCE_COIN = 0.05
PRIOR_CONFIDENCE_EAN = 0.10

MIN_PLANARITY_THRESHOLD = 0.85
MIN_ELLIPSE_FIT_SCORE = 0.80


def resolve_coin_tilt_ambiguity(theta: float, axis: np.ndarray) -> tuple[float, np.ndarray]:
    """Settle the two ambiguities an ellipse fit leaves, by convention and stably.

    An ellipse axis is a line, not a direction: ``fitEllipse`` may hand back ``u`` or
    ``-u`` for the same coin, and a tilt of ``theta`` about one is a tilt of ``-theta``
    about the other. The axis is therefore canonicalised on its *dominant* component
    before any sign is chosen. Keying the sign off ``u_x`` alone is what made this
    function a coin toss: for a vertical major axis ``u_x`` is float noise around zero,
    and OpenCV 4.10 and 5.0 land on opposite sides of it for the same image.

    The tilt direction itself cannot be recovered from the ellipse — a coin leaning
    toward the camera and one leaning away project to the same outline. We assume the top
    of the coin (or, for a vertical axis, its left edge) is further from the camera. A
    capture leaning the other way is rectified with the wrong sign; the error that leaves
    is a few percent near the coin and is not covered by ``PRIOR_CONFIDENCE_COIN``.
    """
    dominant = 0 if abs(axis[0]) >= abs(axis[1]) else 1
    canonical = axis if axis[dominant] > 0 else -axis
    return -float(np.abs(theta)), canonical


def detect_reference_object(
    image: np.ndarray, ref_type: str
) -> tuple[float, float, np.ndarray] | MeasurementRefusal:
    """Detects the reference object in the image and returns
    (mm_per_pixel, confidence_interval, homography_matrix).
    Returns MeasurementRefusal if the object cannot be detected.

    Note on homography: the ``coin_10`` path returns scale only, with
    ``h_matrix`` set to ``None``. A circle under perspective projects to an
    ellipse with no corner correspondences, so any matrix built from its
    bounding box maps arbitrary points — callers must handle ``None`` and
    skip rectification. The consequence is that a coin-calibrated measurement
    on an oblique capture is not perspective-corrected, and
    ``PRIOR_CONFIDENCE_COIN`` does not cover that error. Recovering a real
    homography from the coin by fitting an ellipse is MEA-007.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

    def get_ordered_corners(pts):
        rect = np.zeros((4, 2), dtype="float32")
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        return rect

    def safe_warp(src_pts, w, h, cx, cy):
        dst_pts = np.float32(
            [
                [cx - w / 2, cy - h / 2],
                [cx + w / 2, cy - h / 2],
                [cx + w / 2, cy + h / 2],
                [cx - w / 2, cy + h / 2],
            ]
        )
        return cv2.getPerspectiveTransform(src_pts, dst_pts)

    if ref_type == "coin_10":
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return MeasurementRefusal(reason="Failed to detect reference: No contours found.")

        best_cnt = max(contours, key=cv2.contourArea)
        if len(best_cnt) < 5:
            return MeasurementRefusal(
                reason="Failed to detect reference: too few points for ellipse fit."
            )

        (xc, yc), (w, h), angle_deg = cv2.fitEllipse(best_cnt)
        if w == 0 or h == 0:
            return MeasurementRefusal(reason="Failed to detect reference: Degenerate ellipse fit.")

        angle_rad = np.deg2rad(angle_deg)
        if w > h:
            a, b = w / 2.0, h / 2.0
            u = np.array([np.cos(angle_rad), -np.sin(angle_rad), 0.0])
        else:
            a, b = h / 2.0, w / 2.0
            u = np.array([np.sin(angle_rad), np.cos(angle_rad), 0.0])

        ellipse_area = np.pi * a * b
        contour_area = cv2.contourArea(best_cnt)
        if ellipse_area == 0 or contour_area == 0:
            return MeasurementRefusal(
                reason=("Failed to detect reference: Zero area contour or ellipse.")
            )

        fit_confidence = min(ellipse_area, contour_area) / max(ellipse_area, contour_area)
        if fit_confidence < MIN_ELLIPSE_FIT_SCORE:
            return MeasurementRefusal(
                reason=(
                    "Failed to detect reference: "
                    f"Ellipse fit not confident (score {fit_confidence:.2f})."
                )
            )

        # The coin is a circle tilted in place, so its major axis is the one diameter left
        # unforeshortened: that is the axis it tilted about, and b/a is the cosine of the tilt.
        theta, u = resolve_coin_tilt_ambiguity(float(np.arccos(b / a)), u)
        k_u = np.array([[0.0, -u[2], u[1]], [u[2], 0.0, -u[0]], [-u[1], u[0], 0.0]])
        r_tilt = np.eye(3) + np.sin(theta) * k_u + (1.0 - np.cos(theta)) * (k_u @ k_u)

        # A pseudo-camera centred on the coin, focal length = image diagonal, with the coin's
        # plane at depth f so one plane unit is one pixel when fronto-parallel. The plane
        # maps to the image as K [r1 r2 t]; rectifying it is undoing that and re-imaging the
        # same plane untilted, K [e1 e2 t]. Scale at the coin centre is preserved exactly.
        h_img, w_img = gray.shape
        f_val = np.sqrt(w_img**2 + h_img**2)
        k_mat = np.array([[f_val, 0.0, xc], [0.0, f_val, yc], [0.0, 0.0, 1.0]])
        depth = np.array([0.0, 0.0, f_val])
        tilted = np.column_stack([r_tilt[:, 0], r_tilt[:, 1], depth])
        fronto = np.column_stack([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], depth])
        h_matrix = k_mat @ fronto @ np.linalg.inv(tilted) @ np.linalg.inv(k_mat)

        diameter_px = a * 2.0
        scale = REF_DIMS["coin_10"]["diameter_mm"] / diameter_px

        return scale, (scale * PRIOR_CONFIDENCE_COIN) / fit_confidence, h_matrix

    elif ref_type == "id_card":
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return MeasurementRefusal(
                reason="Rectification failed: unable to identify adequately planar panel"
            )

        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        best_box = None
        best_cnt = None
        for cnt in contours:
            epsilon = 0.02 * cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, epsilon, True)
            if len(approx) == 4:
                best_box = approx.reshape(4, 2)
                best_cnt = cnt
                break

        if best_box is None:
            best_cnt = contours[0]
            rect = cv2.minAreaRect(best_cnt)
            best_box = cv2.boxPoints(rect)

        src_pts = get_ordered_corners(best_box)
        rect = cv2.minAreaRect(best_cnt)
        cx, cy = rect[0]
        w, h = rect[1]
        if max(w, h) == 0:
            return MeasurementRefusal(
                reason="Rectification failed: unable to identify adequately planar panel"
            )

        d01 = np.linalg.norm(src_pts[0] - src_pts[1])
        d12 = np.linalg.norm(src_pts[1] - src_pts[2])
        if d01 > d12:
            dst_w = max(w, h)
            dst_h = dst_w * (53.98 / 85.60)
        else:
            dst_h = max(w, h)
            dst_w = dst_h * (53.98 / 85.60)

        h_matrix = safe_warp(src_pts, dst_w, dst_h, cx, cy)
        warped = cv2.warpPerspective(
            gray, h_matrix, (gray.shape[1], gray.shape[0]), borderValue=255
        )

        edges = cv2.Canny(warped, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            c = max(contours, key=cv2.contourArea)
            rect = cv2.minAreaRect(c)
            w, h = rect[1]
            if max(w, h) > 0:
                scale = REF_DIMS["id_card"]["width_mm"] / max(w, h)
                return scale, scale * PRIOR_CONFIDENCE_CARD, h_matrix
        return MeasurementRefusal(reason=f"Failed to detect reference object of type: {ref_type}.")

    elif ref_type == "ean_13":
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobelx = cv2.convertScaleAbs(sobelx)
        _, thresh = cv2.threshold(sobelx, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (21, 7))
        closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(closed.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return MeasurementRefusal(
                reason="Rectification failed: unable to identify adequately planar panel"
            )

        c = max(contours, key=cv2.contourArea)
        rect = cv2.minAreaRect(c)
        src_pts = get_ordered_corners(cv2.boxPoints(rect))
        cx, cy = rect[0]

        dst_w = float(np.linalg.norm(src_pts[0] - src_pts[1]))
        if dst_w == 0:
            return MeasurementRefusal(
                reason="Rectification failed: unable to identify adequately planar panel"
            )

        dst_h = dst_w * (25.93 / 37.29)  # True EAN-13 aspect ratio

        h_matrix = safe_warp(src_pts, dst_w, dst_h, cx, cy)
        warped = cv2.warpPerspective(
            gray, h_matrix, (gray.shape[1], gray.shape[0]), borderValue=255
        )

        sobelx = cv2.Sobel(warped, cv2.CV_64F, 1, 0, ksize=3)
        sobelx = cv2.convertScaleAbs(sobelx)
        _, thresh = cv2.threshold(sobelx, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(closed.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if contours:
            c = max(contours, key=cv2.contourArea)
            rect = cv2.minAreaRect(c)
            w, h = rect[1]
            if max(w, h) > 0:
                scale = REF_DIMS["ean_13"]["width_mm"] / max(w, h)
                return scale, scale * PRIOR_CONFIDENCE_EAN, h_matrix
        return MeasurementRefusal(reason=f"Failed to detect reference object of type: {ref_type}.")

    return MeasurementRefusal(
        reason="Rectification failed: unable to identify adequately planar panel"
    )


Region = tuple[int, int, int, int]
"""``(x, y, width, height)`` in the pixel coordinates of the frame handed in."""


def _ink_mask(gray: np.ndarray, declaration: Region | None = None) -> np.ndarray:
    """Otsu-threshold a frame so that ink is 255, whichever way round the label is printed.

    Otsu separates two classes and cannot say which one is the ink. Assuming the darker one
    is right for black on white and wrong for white on a dark panel, where it marks the
    whole background as ink and every margin comes back as an overlap.

    Two ways to tell, by what was handed in. Around a whole frame, a declaration's own box
    decides: inside it the ink is the minority of the pixels. For a crop with no box — one
    numeral, padded — the border decides: a crop is cut around its ink, so whatever covers
    most of its outermost pixels is the background.
    """
    _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    if declaration is not None:
        x, y, w, h = declaration
        sample = mask[max(0, y) : y + h, max(0, x) : x + w]
    else:
        sample = np.concatenate([mask[0, :], mask[-1, :], mask[:, 0], mask[:, -1]])
    if sample.size and np.count_nonzero(sample) * 2 > sample.size:
        mask = cv2.bitwise_not(mask)
    return mask


def _warp_region(region: Region, h_matrix: np.ndarray | None) -> Region:
    """The axis-aligned box a region occupies once the frame has been rectified."""
    x, y, w, h = region
    if h_matrix is None:
        return region
    pts = np.array([[[x, y], [x + w, y], [x + w, y + h], [x, y + h]]], dtype=np.float32)
    warped = cv2.perspectiveTransform(pts, h_matrix)[0]
    x0, y0 = max(0, int(np.min(warped[:, 0]))), max(0, int(np.min(warped[:, 1])))
    return x0, y0, int(np.max(warped[:, 0])) - x0, int(np.max(warped[:, 1])) - y0


def _crop(image: np.ndarray, region: Region | None) -> np.ndarray:
    if region is None:
        return image
    x, y, w, h = region
    return image[max(0, y) : y + h, max(0, x) : x + w]


def measure_ink_extent(
    image: np.ndarray,
    ref_image: np.ndarray | None = None,
    ref_type: str | None = None,
    is_artwork: bool = False,
    artwork_dpi: float | None = None,
    region: Region | None = None,
) -> MeasurementResult:
    """Measure the true ink extent (height) of a cropped numeral image.
    Uses reference object detection for calibration, or exact DPI if artwork.
    """
    if is_artwork:
        if artwork_dpi is None or artwork_dpi <= 0:
            return MeasurementRefusal(
                reason=("Missing or invalid artwork_dpi for exact measurement.")
            )
        mm_per_pixel = 25.4 / artwork_dpi
    else:
        if ref_image is None or ref_type is None:
            return MeasurementRefusal(
                reason=("Missing reference object image or type for calibration.")
            )
        calib = detect_reference_object(ref_image, ref_type)
        if isinstance(calib, MeasurementRefusal):
            return calib
        mm_per_pixel, conf_interval, h_matrix = calib

        # Warp the original image using homography if supported
        bw = (255, 255, 255) if len(image.shape) == 3 else 255
        if h_matrix is not None:
            image = cv2.warpPerspective(
                image, h_matrix, (image.shape[1], image.shape[0]), borderValue=bw
            )
            region = _warp_region(region, h_matrix) if region is not None else None

    # A region is a box in the frame as photographed; it is cropped only here, after the
    # frame has been rectified, because the homography is in whole-frame coordinates and
    # warping a crop with it would move the crop somewhere else entirely.
    image = _crop(image, region)
    if image.size == 0:
        return MeasurementRefusal(reason="The region to measure lies outside the frame.")

    # Convert numeral image to grayscale if needed
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

    thresh = _ink_mask(gray)

    # Measure true ink extent (first-to-last active pixel row)
    active_pixels = cv2.findNonZero(thresh)
    if active_pixels is None:
        return MeasurementRefusal(reason="No ink detected in the image.")

    # Defensively reshape to (-1, 2) to handle OpenCV cross-version binding differences
    active_pixels = active_pixels.reshape(-1, 2)
    y_coords = active_pixels[:, 1]
    min_y = np.min(y_coords)
    max_y = np.max(y_coords)
    height_px = max_y - min_y + 1

    # Calculate height in mm
    height_mm = height_px * mm_per_pixel

    if is_artwork:
        return MeasurementExact(value=height_mm, unit="mm")

    confidence = height_px * conf_interval

    return MeasurementCalibrated(
        value=height_mm, confidence_interval=confidence, unit="mm", reference_object=ref_type
    )


def _compute_rule_7_area(
    height_mm: float, width_mm: float, shape: PackageShape
) -> tuple[float, str]:
    if shape == PackageShape.RECTANGULAR:
        area_mm2 = height_mm * width_mm
        rule_limb = "rectangular"
    elif shape == PackageShape.CYLINDRICAL:
        area_mm2 = 0.40 * (height_mm * (np.pi * width_mm))
        rule_limb = "cylindrical 40%"
    else:
        area_mm2 = height_mm * width_mm
        rule_limb = "other-panel-measured"

    return area_mm2 / 100.0, rule_limb


def calculate_pdp_area(
    image: np.ndarray,
    ref_image: np.ndarray | None = None,
    ref_type: str | None = None,
    shape: PackageShape = PackageShape.RECTANGULAR,
    planarity_score: float = 1.0,
    is_artwork: bool = False,
    artwork_dpi: float | None = None,
) -> MeasurementResult:
    """Calculate the Principal Display Panel (PDP) area in cm² according to Rule 7(4)."""
    if is_artwork:
        if artwork_dpi is None or artwork_dpi <= 0:
            return MeasurementRefusal(
                reason=("Missing or invalid artwork_dpi for exact measurement.")
            )
        mm_per_pixel = 25.4 / artwork_dpi
    else:
        if ref_image is None or ref_type is None:
            return MeasurementRefusal(
                reason=("Missing reference object image or type for calibration.")
            )
        calib = detect_reference_object(ref_image, ref_type)
        if isinstance(calib, MeasurementRefusal):
            return calib
        mm_per_pixel, conf_interval, h_matrix = calib
        bw = (255, 255, 255) if len(image.shape) == 3 else 255
        if h_matrix is not None:
            image = cv2.warpPerspective(
                image, h_matrix, (image.shape[1], image.shape[0]), borderValue=bw
            )

    if shape == PackageShape.OTHER and planarity_score < MIN_PLANARITY_THRESHOLD:
        return MeasurementRefusal(reason="Panel is not adequately planar for homography.")

    height_px, width_px = image.shape[:2]
    height_mm = height_px * mm_per_pixel
    width_mm = width_px * mm_per_pixel

    area_cm2, rule_limb = _compute_rule_7_area(height_mm, width_mm, shape)

    if is_artwork:
        return MeasurementExact(value=area_cm2, unit="cm²", rule_limb=rule_limb)

    rel_conf = conf_interval / mm_per_pixel
    confidence = area_cm2 * (rel_conf * 2)

    return MeasurementCalibrated(
        value=area_cm2,
        confidence_interval=confidence,
        unit="cm²",
        reference_object=ref_type,
        rule_limb=rule_limb,
    )


def measure_contrast_ratio(text_crop: np.ndarray, bg_crop: np.ndarray) -> MeasurementResult:
    """Measure the WCAG 2.1 contrast ratio between text and background crops."""

    # Convert to standard RGB (OpenCV uses BGR by default if 3 channels)
    def to_rgb(crop: np.ndarray) -> np.ndarray:
        if len(crop.shape) == 3 and crop.shape[2] == 3:
            return cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        elif len(crop.shape) == 2:
            return cv2.cvtColor(crop, cv2.COLOR_GRAY2RGB)
        return crop

    text_rgb = to_rgb(text_crop)
    bg_rgb = to_rgb(bg_crop)

    # Calculate means (R, G, B) normalized to 0-1
    text_mean = np.mean(text_rgb, axis=(0, 1)) / 255.0
    bg_mean = np.mean(bg_rgb, axis=(0, 1)) / 255.0

    # Relative luminance helper
    def relative_luminance(rgb: np.ndarray) -> float:
        rgb = np.where(rgb <= 0.03928, rgb / 12.92, np.power((rgb + 0.055) / 1.055, 2.4))
        return float(0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2])

    l1 = relative_luminance(text_mean)
    l2 = relative_luminance(bg_mean)

    # Ensure L1 is lighter
    if l1 < l2:
        l1, l2 = l2, l1

    contrast_ratio = (l1 + 0.05) / (l2 + 0.05)

    # Calculate a rough confidence interval based on pixel variance
    # We take standard deviation of luminance across the crops
    def get_luminances(rgb_crop: np.ndarray) -> np.ndarray:
        flat = rgb_crop.reshape(-1, 3) / 255.0
        flat = np.where(flat <= 0.03928, flat / 12.92, np.power((flat + 0.055) / 1.055, 2.4))
        return 0.2126 * flat[:, 0] + 0.7152 * flat[:, 1] + 0.0722 * flat[:, 2]

    text_lums = get_luminances(text_rgb)
    bg_lums = get_luminances(bg_rgb)

    # Variance mapping to confidence interval.
    # Higher standard deviation = wider confidence interval.
    # It's a heuristic for MeasurementCalibrated to show "confidence"
    std_combined = float(np.std(text_lums) + np.std(bg_lums))
    confidence = std_combined * contrast_ratio

    return MeasurementCalibrated(
        value=contrast_ratio,
        confidence_interval=confidence,
        unit="ratio",
        reference_object="color_variance",
    )


def measure_width_to_height_ratio(
    image: np.ndarray,
    ref_image: np.ndarray | None = None,
    ref_type: str | None = None,
    is_artwork: bool = False,
    artwork_dpi: float | None = None,
    region: Region | None = None,
) -> MeasurementResult:
    """Measure the width-to-height ratio of a cropped numeral image."""
    if is_artwork:
        if artwork_dpi is None or artwork_dpi <= 0:
            return MeasurementRefusal(
                reason=("Missing or invalid artwork_dpi for exact measurement.")
            )
    else:
        if ref_image is None or ref_type is None:
            return MeasurementRefusal(
                reason=("Missing reference object image or type for calibration.")
            )
        calib = detect_reference_object(ref_image, ref_type)
        if isinstance(calib, MeasurementRefusal):
            return calib
        mm_per_pixel, conf_interval, h_matrix = calib
        bw = (255, 255, 255) if len(image.shape) == 3 else 255
        if h_matrix is not None:
            image = cv2.warpPerspective(
                image, h_matrix, (image.shape[1], image.shape[0]), borderValue=bw
            )
            region = _warp_region(region, h_matrix) if region is not None else None

    # A region is a box in the frame as photographed; it is cropped only here, after the
    # frame has been rectified, because the homography is in whole-frame coordinates and
    # warping a crop with it would move the crop somewhere else entirely.
    image = _crop(image, region)
    if image.size == 0:
        return MeasurementRefusal(reason="The region to measure lies outside the frame.")

    # Convert numeral image to grayscale if needed
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

    thresh = _ink_mask(gray)

    active_pixels = cv2.findNonZero(thresh)
    if active_pixels is None:
        return MeasurementRefusal(reason="No ink detected in the image.")

    active_pixels = active_pixels.reshape(-1, 2)
    x_coords = active_pixels[:, 0]
    y_coords = active_pixels[:, 1]

    width_px = np.max(x_coords) - np.min(x_coords) + 1
    height_px = np.max(y_coords) - np.min(y_coords) + 1

    if height_px == 0:
        return MeasurementRefusal(reason="Height of ink is zero, cannot calculate ratio.")

    ratio = float(width_px) / float(height_px)

    if is_artwork:
        return MeasurementExact(value=ratio, unit="ratio")

    # Note: The scale error cancels between the numerator and denominator,
    # making this calculated interval wider than the truth.
    # This safely errs toward REVIEW rather than PASS.
    rel_conf = conf_interval / mm_per_pixel
    confidence = ratio * rel_conf

    return MeasurementCalibrated(
        value=ratio, confidence_interval=confidence, unit="ratio", reference_object=ref_type
    )


def measure_margins(
    image: np.ndarray,
    declaration_bbox: tuple[int, int, int, int],
    ref_image: np.ndarray | None = None,
    ref_type: str | None = None,
    is_artwork: bool = False,
    artwork_dpi: float | None = None,
) -> MeasurementMarginSet:
    """Measure the margins around a declaration bounding box."""

    def make_refusals(reason: str) -> MeasurementMarginSet:
        return MeasurementMarginSet(
            **{
                direction: MeasurementRefusal(reason=reason)
                for direction in ("above", "below", "left", "right")
            }
        )

    if is_artwork:
        if artwork_dpi is None or artwork_dpi <= 0:
            return make_refusals("Missing or invalid artwork_dpi for exact measurement.")
        mm_per_pixel = 25.4 / artwork_dpi
    else:
        if ref_image is None or ref_type is None:
            return make_refusals("Missing reference object image or type for calibration.")
        calib = detect_reference_object(ref_image, ref_type)
        if isinstance(calib, MeasurementRefusal):
            return make_refusals(calib.reason)
        mm_per_pixel, conf_interval, h_matrix = calib
        bw = (255, 255, 255) if len(image.shape) == 3 else 255
        if h_matrix is not None:
            image = cv2.warpPerspective(
                image, h_matrix, (image.shape[1], image.shape[0]), borderValue=bw
            )

    x, y, w, h = declaration_bbox
    if not is_artwork and h_matrix is not None:
        pts = np.array([[[x, y], [x + w, y], [x + w, y + h], [x, y + h]]], dtype=np.float32)
        warped_pts = cv2.perspectiveTransform(pts, h_matrix)
        x_coords = warped_pts[0, :, 0]
        y_coords = warped_pts[0, :, 1]
        x = max(0, int(np.min(x_coords)))
        y = max(0, int(np.min(y_coords)))
        w = int(np.max(x_coords)) - x
        h = int(np.max(y_coords)) - y
    img_h, img_w = image.shape[:2]
    mid_y = y + h // 2
    mid_x = x + w // 2

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    thresh = _ink_mask(gray, (x, y, w, h))

    # The box holds the declaration's own print, which is not printed information
    # *surrounding* it. A component centred inside the box is the declaration; it is lifted
    # out of the mask and the box is redrawn around it, so clearance runs from the ink and
    # not from however much padding the OCR polygon carried. A component centred outside
    # that reaches in is a neighbour, stays in the mask, and is what an overlap is.
    count, labels, stats, centroids = cv2.connectedComponentsWithStats(thresh, connectivity=8)
    own = [
        index
        for index in range(1, count)
        if x <= centroids[index][0] < x + w and y <= centroids[index][1] < y + h
    ]
    if own:
        thresh[np.isin(labels, own)] = 0
        left_edge = min(int(stats[index, cv2.CC_STAT_LEFT]) for index in own)
        top_edge = min(int(stats[index, cv2.CC_STAT_TOP]) for index in own)
        right_edge = max(
            int(stats[index, cv2.CC_STAT_LEFT] + stats[index, cv2.CC_STAT_WIDTH]) for index in own
        )
        bottom_edge = max(
            int(stats[index, cv2.CC_STAT_TOP] + stats[index, cv2.CC_STAT_HEIGHT]) for index in own
        )
        x, y, w, h = left_edge, top_edge, right_edge - left_edge, bottom_edge - top_edge
        mid_y, mid_x = y + h // 2, x + w // 2

    # Distances in pixels
    distances_px = {}

    # Above
    # Rule 8(1) is about the area *surrounding* the declaration. Ink counts above or below
    # only within the declaration's own columns, and left or right only within its own rows:
    # measured across the whole frame, a logo in the far corner becomes the nearest ink
    # "above" and every real label fails.
    # ponytail: the four corner blocks of the clear zone are not searched. Widening each
    # band by the required clearance needs the numeral height, which this function is not given.
    above_slice = thresh[0:mid_y, :].copy()
    above_slice[:, 0:x] = 0
    above_slice[:, x + w :] = 0
    active_above = cv2.findNonZero(above_slice)
    if active_above is not None:
        max_y = np.max(active_above.reshape(-1, 2)[:, 1])
        distances_px["above"] = y - max_y - 1
    else:
        distances_px["above"] = y

    # Below
    below_slice = thresh[mid_y:img_h, :].copy()
    below_slice[:, 0:x] = 0
    below_slice[:, x + w :] = 0
    active_below = cv2.findNonZero(below_slice)
    if active_below is not None:
        min_y = np.min(active_below.reshape(-1, 2)[:, 1])
        distances_px["below"] = min_y + mid_y - (y + h)
    else:
        distances_px["below"] = img_h - (y + h)

    # Left
    left_slice = thresh[:, 0:mid_x].copy()
    left_slice[0:y, :] = 0
    left_slice[y + h :, :] = 0
    active_left = cv2.findNonZero(left_slice)
    if active_left is not None:
        max_x = np.max(active_left.reshape(-1, 2)[:, 0])
        distances_px["left"] = x - max_x - 1
    else:
        distances_px["left"] = x

    # Right
    right_slice = thresh[:, mid_x:img_w].copy()
    right_slice[0:y, :] = 0
    right_slice[y + h :, :] = 0
    active_right = cv2.findNonZero(right_slice)
    if active_right is not None:
        min_x = np.min(active_right.reshape(-1, 2)[:, 0])
        distances_px["right"] = min_x + mid_x - (x + w)
    else:
        distances_px["right"] = img_w - (x + w)

    results = {}
    for direction, dist_px in distances_px.items():
        dist_mm = dist_px * mm_per_pixel
        if dist_mm < 0:
            if is_artwork:
                results[direction] = MeasurementMarginOverlapExact(overlap=abs(dist_mm), unit="mm")
            else:
                confidence_floor = UNCALIBRATED_QUANTISATION_PRIOR_PX * mm_per_pixel
                confidence = max(abs(dist_px) * conf_interval, confidence_floor)
                results[direction] = MeasurementMarginOverlapCalibrated(
                    overlap=abs(dist_mm),
                    confidence_interval=confidence,
                    unit="mm",
                    reference_object=ref_type,
                )
            continue

        if is_artwork:
            results[direction] = MeasurementMarginExact(value=dist_mm, unit="mm")
        else:
            # Floor confidence at 1 pixel's mm equivalent to account for quantisation
            confidence_floor = UNCALIBRATED_QUANTISATION_PRIOR_PX * mm_per_pixel
            confidence = max(abs(dist_px) * conf_interval, confidence_floor)
            results[direction] = MeasurementMarginCalibrated(
                value=dist_mm,
                confidence_interval=confidence,
                unit="mm",
                reference_object=ref_type,
            )

    return MeasurementMarginSet(**results)


MIN_GLYPH_AREA_PX = 4
"""Connected components smaller than this are sensor or JPEG speckle, not print. A full
stop in a 2 mm declaration photographed at arm's length is still a dozen pixels."""


def segment_declaration_glyphs(
    image: np.ndarray, declaration_bbox: Region, text: str
) -> tuple[tuple[str, Region], ...] | MeasurementRefusal:
    """Find each printed character of a declaration, and say which character it is.

    Rule 7(3) is a rule about one character at a time and exempts four of them by name, so
    a width-to-height figure is only evidence once it is attached to a character. OCR gives
    the text of a line and a box around the line; this splits the box into glyphs by
    connected components and pairs them with the text left to right.

    The pairing is only made when the counts agree. Touching print, a broken stroke or a
    misread character all leave more or fewer glyphs than characters, and at that point
    nothing says which glyph is the "1" — so this refuses rather than guessing, and the
    rule reports INSUFFICIENT_EVIDENCE. Pixels only: no millimetre is produced here.
    """
    x, y, w, h = declaration_bbox
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    window = _ink_mask(gray, declaration_bbox)[max(0, y) : y + h, max(0, x) : x + w]
    if window.size == 0:
        return MeasurementRefusal(reason="The declaration's region lies outside the frame.")

    _, _, stats, _ = cv2.connectedComponentsWithStats(window, connectivity=8)
    parts = sorted(
        (int(sx), int(sy), int(sw), int(sh))
        for sx, sy, sw, sh, area in stats[1:]
        if area >= MIN_GLYPH_AREA_PX
    )
    # The dot of an "i", both marks of a colon: components stacked in one column are one glyph.
    columns: list[list[int]] = []
    for sx, sy, sw, sh in parts:
        if columns and sx < columns[-1][2]:
            left, top, right, bottom = columns[-1]
            columns[-1] = [left, min(top, sy), max(right, sx + sw), max(bottom, sy + sh)]
        else:
            columns.append([sx, sy, sx + sw, sy + sh])

    characters = [character for character in text if not character.isspace()]
    if len(columns) != len(characters):
        return MeasurementRefusal(
            reason=(
                f"The declaration reads as {len(characters)} characters and {len(columns)} "
                "separate glyphs were found in its region, so no glyph can be matched to a "
                "character — the print is touching, broken, or was misread."
            )
        )
    origin_x, origin_y = max(0, x), max(0, y)
    return tuple(
        (character, (origin_x + left, origin_y + top, right - left, bottom - top))
        for character, (left, top, right, bottom) in zip(characters, columns, strict=True)
    )


def measure_panel_dimensions(
    image: np.ndarray,
    panel_bbox: Region,
    ref_image: np.ndarray | None = None,
    ref_type: str | None = None,
    is_artwork: bool = False,
    artwork_dpi: float | None = None,
) -> tuple[MeasurementResult, MeasurementResult]:
    """Height and width of the detected principal display panel, in millimetres.

    Dimensions rather than an area: Rule 7(4) turns them into an area differently for each
    package shape, and its multipliers live in the rule store, which this module may not
    import. Both results are refusals together or measurements together.
    """
    if is_artwork:
        if artwork_dpi is None or artwork_dpi <= 0:
            refusal = MeasurementRefusal(
                reason="Missing or invalid artwork_dpi for exact measurement."
            )
            return refusal, refusal
        _, _, width_px, height_px = panel_bbox
        mm_per_pixel = 25.4 / artwork_dpi
        return (
            MeasurementExact(value=height_px * mm_per_pixel, unit="mm"),
            MeasurementExact(value=width_px * mm_per_pixel, unit="mm"),
        )

    if ref_image is None or ref_type is None:
        refusal = MeasurementRefusal(
            reason="Missing reference object image or type for calibration."
        )
        return refusal, refusal
    calib = detect_reference_object(ref_image, ref_type)
    if isinstance(calib, MeasurementRefusal):
        return calib, calib
    mm_per_pixel, conf_interval, h_matrix = calib
    _, _, width_px, height_px = _warp_region(panel_bbox, h_matrix)
    if width_px <= 0 or height_px <= 0:
        refusal = MeasurementRefusal(reason="The detected panel has no extent once rectified.")
        return refusal, refusal
    return (
        MeasurementCalibrated(
            value=height_px * mm_per_pixel,
            confidence_interval=height_px * conf_interval,
            unit="mm",
            reference_object=ref_type,
        ),
        MeasurementCalibrated(
            value=width_px * mm_per_pixel,
            confidence_interval=width_px * conf_interval,
            unit="mm",
            reference_object=ref_type,
        ),
    )


def measure_declaration_contrast(image: np.ndarray, declaration_bbox: Region) -> MeasurementResult:
    """Contrast between a declaration's print and the label behind it, inside its own box.

    Splits the box into ink and background with the same mask every other measurement here
    uses, and hands the two pixel sets to :func:`measure_contrast_ratio`. No calibration is
    involved and none is needed: a contrast ratio has no physical unit. It does depend on
    the lighting the photograph was taken in, which is why it is evidence for an officer and
    never a figure a threshold is applied to.
    """
    x, y, w, h = declaration_bbox
    window = _crop(image, declaration_bbox)
    if window.size == 0:
        return MeasurementRefusal(reason="The declaration's region lies outside the frame.")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    ink = _ink_mask(gray, declaration_bbox)[max(0, y) : y + h, max(0, x) : x + w] > 0
    if not ink.any() or ink.all():
        return MeasurementRefusal(
            reason="The declaration's region could not be separated into print and background."
        )
    return measure_contrast_ratio(window[ink][:, None], window[~ink][:, None])
