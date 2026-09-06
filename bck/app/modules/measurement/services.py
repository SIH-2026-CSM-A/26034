import cv2
import numpy as np

from app.contracts import (
    MeasurementCalibrated,
    MeasurementExact,
    MeasurementRefusal,
    MeasurementResult,
)

from .schemas import PackageShape

# Reference object physical dimensions
REF_DIMS = {
    "id_card": {"width_mm": 85.60, "height_mm": 53.98},
    "coin_10": {"diameter_mm": 27.0},
    "ean_13": {"width_mm": 37.29},
}

MIN_PLANARITY_THRESHOLD = 0.85


def detect_reference_object(
    image: np.ndarray, ref_type: str
) -> tuple[float, float, np.ndarray] | MeasurementRefusal:
    """Detects the reference object in the image and returns
    (mm_per_pixel, confidence_interval, homography_matrix).
    Returns MeasurementRefusal if the object cannot be detected.
    
    Note on homography: The `coin_10` path cannot recover a true projective homography. 
    A circle under perspective becomes an ellipse with no distinct corners, meaning the 
    bounding box maps arbitrary points. It recovers scale and aspect, but should not be 
    trusted for highly oblique camera angles.
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
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return MeasurementRefusal(
                reason="Rectification failed: unable to identify adequately planar panel"
            )
        c = max(contours, key=cv2.contourArea)
        rect = cv2.minAreaRect(c)
        src_pts = get_ordered_corners(cv2.boxPoints(rect))

        cx, cy = rect[0]
        side = max(rect[1])
        if side == 0:
            return MeasurementRefusal(
                reason="Rectification failed: unable to identify adequately planar panel"
            )

        h_matrix = safe_warp(src_pts, side, side, cx, cy)
        warped = cv2.warpPerspective(
            gray, h_matrix, (gray.shape[1], gray.shape[0]), borderValue=255
        )

        blurred = cv2.medianBlur(warped, 5)
        circles = cv2.HoughCircles(
            blurred,
            cv2.HOUGH_GRADIENT,
            dp=1,
            minDist=20,
            param1=50,
            param2=30,
            minRadius=10,
            maxRadius=max(warped.shape) // 2,
        )
        if circles is not None and len(circles) > 0:
            circles = np.uint16(np.around(circles))
            max_circle = max(circles[0, :], key=lambda c: c[2])
            diameter_px = max_circle[2] * 2
            if diameter_px > 0:
                scale = REF_DIMS["coin_10"]["diameter_mm"] / diameter_px
                return scale, scale * 0.05, h_matrix
        return MeasurementRefusal(reason=f"Failed to detect reference object of type: {ref_type}.")

    elif ref_type == "id_card":
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return MeasurementRefusal(
                reason="Rectification failed: unable to identify adequately planar panel"
            )

        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        best_box = None
        for cnt in contours:
            epsilon = 0.02 * cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, epsilon, True)
            if len(approx) == 4:
                best_box = approx.reshape(4, 2)
                break

        if best_box is None:
            rect = cv2.minAreaRect(contours[0])
            best_box = cv2.boxPoints(rect)

        src_pts = get_ordered_corners(best_box)
        rect = cv2.minAreaRect(contours[0])
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
                return scale, scale * 0.01, h_matrix
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
                return scale, scale * 0.10, h_matrix
        return MeasurementRefusal(reason=f"Failed to detect reference object of type: {ref_type}.")

    return MeasurementRefusal(
        reason="Rectification failed: unable to identify adequately planar panel"
    )


def measure_ink_extent(
    image: np.ndarray,
    ref_image: np.ndarray | None = None,
    ref_type: str | None = None,
    is_artwork: bool = False,
    artwork_dpi: float | None = None,
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

        # Warp the original image using homography
        bw = (255, 255, 255) if len(image.shape) == 3 else 255
        image = cv2.warpPerspective(
            image, h_matrix, (image.shape[1], image.shape[0]), borderValue=bw
        )

    # Convert numeral image to grayscale if needed
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

    # Apply Otsu thresholding. Assume ink is darker than background,
    # so we want ink to be 255 (active). We use THRESH_BINARY_INV.
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

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
        image = cv2.warpPerspective(
            image, h_matrix, (image.shape[1], image.shape[0]), borderValue=bw
        )

    height_px, width_px = image.shape[:2]
    height_mm = height_px * mm_per_pixel
    width_mm = width_px * mm_per_pixel

    # Calculate area in mm² based on shape
    if shape == PackageShape.RECTANGULAR:
        area_mm2 = height_mm * width_mm
        rule_limb = "rectangular"
    elif shape == PackageShape.CYLINDRICAL:
        area_mm2 = 0.40 * (height_mm * (np.pi * width_mm))
        rule_limb = "cylindrical 40%"
    else:  # OTHER
        if planarity_score < MIN_PLANARITY_THRESHOLD:
            return MeasurementRefusal(reason="Panel is not adequately planar for homography.")
        area_mm2 = height_mm * width_mm
        rule_limb = "other-panel-measured"

    # Convert to cm²
    area_cm2 = area_mm2 / 100.0

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
        image = cv2.warpPerspective(
            image, h_matrix, (image.shape[1], image.shape[0]), borderValue=bw
        )

    # Convert numeral image to grayscale if needed
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

    # Apply Otsu thresholding
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

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
) -> dict[str, MeasurementResult]:
    """Measure the margins around a declaration bounding box."""

    def make_refusals(reason: str) -> dict[str, MeasurementResult]:
        return {
            direction: MeasurementRefusal(reason=reason)
            for direction in ("above", "below", "left", "right")
        }

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

    # Convert numeral image to grayscale if needed
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

    # Apply Otsu thresholding
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Distances in pixels
    distances_px = {}

    # Above
    above_slice = thresh[0:y, :]
    active_above = cv2.findNonZero(above_slice)
    if active_above is not None:
        max_y = np.max(active_above.reshape(-1, 2)[:, 1])
        distances_px["above"] = y - max_y - 1
    else:
        distances_px["above"] = y

    # Below
    below_slice = thresh[y + h : img_h, :]
    active_below = cv2.findNonZero(below_slice)
    if active_below is not None:
        min_y = np.min(active_below.reshape(-1, 2)[:, 1])
        distances_px["below"] = min_y
    else:
        distances_px["below"] = img_h - (y + h)

    # Left
    left_slice = thresh[:, 0:x]
    active_left = cv2.findNonZero(left_slice)
    if active_left is not None:
        max_x = np.max(active_left.reshape(-1, 2)[:, 0])
        distances_px["left"] = x - max_x - 1
    else:
        distances_px["left"] = x

    # Right
    right_slice = thresh[:, x + w : img_w]
    active_right = cv2.findNonZero(right_slice)
    if active_right is not None:
        min_x = np.min(active_right.reshape(-1, 2)[:, 0])
        distances_px["right"] = min_x
    else:
        distances_px["right"] = img_w - (x + w)

    results = {}
    for direction, dist_px in distances_px.items():
        dist_mm = max(0, dist_px) * mm_per_pixel
        if is_artwork:
            results[direction] = MeasurementExact(value=dist_mm, unit="mm")
        else:
            confidence = max(0, dist_px) * conf_interval
            results[direction] = MeasurementCalibrated(
                value=dist_mm,
                confidence_interval=confidence,
                unit="mm",
                reference_object=ref_type,
            )

    return results
