import cv2
import numpy as np

from .schemas import MeasurementCalibrated, MeasurementRefusal, MeasurementResult, PackageShape

# Reference object physical dimensions
REF_DIMS = {
    "id_card": {"width_mm": 85.60, "height_mm": 53.98},
    "coin_10": {"diameter_mm": 27.0},
    "ean_13": {"width_mm": 37.29},
}

MIN_PLANARITY_THRESHOLD = 0.85


def detect_reference_object(image: np.ndarray, ref_type: str) -> float | None:
    """Detects the reference object in the image and returns mm_per_pixel scale factor.
    Returns None if the object cannot be detected."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

    if ref_type == "coin_10":
        # Blur before Hough circles
        blurred = cv2.medianBlur(gray, 5)
        circles = cv2.HoughCircles(
            blurred,
            cv2.HOUGH_GRADIENT,
            dp=1,
            minDist=20,
            param1=50,
            param2=30,
            minRadius=10,
            maxRadius=max(gray.shape) // 2,
        )
        if circles is not None and len(circles) > 0:
            circles = np.uint16(np.around(circles))
            # Take the largest circle as the coin
            max_circle = max(circles[0, :], key=lambda c: c[2])
            radius_px = max_circle[2]
            diameter_px = radius_px * 2
            if diameter_px > 0:
                return REF_DIMS["coin_10"]["diameter_mm"] / diameter_px
        return None

    elif ref_type == "id_card":
        # Edge detection and contour finding
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        # Find largest rectangular contour
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        for cnt in contours:
            epsilon = 0.02 * cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, epsilon, True)
            if len(approx) == 4:
                rect = cv2.minAreaRect(cnt)
                w, h = rect[1]
                if w == 0 or h == 0:
                    continue
                # ID card aspect ratio is 85.60 / 53.98 ≈ 1.585
                aspect = max(w, h) / min(w, h)
                if 1.4 < aspect < 1.8:
                    return REF_DIMS["id_card"]["width_mm"] / max(w, h)
        return None

    elif ref_type == "ean_13":
        # Simplified barcode detection: find largest bounding box of high frequency vertical edges
        # We can use Sobel to find vertical edges
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobelx = cv2.convertScaleAbs(sobelx)
        _, thresh = cv2.threshold(sobelx, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Morphological close to group lines together
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (21, 7))
        closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(closed.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        c = max(contours, key=cv2.contourArea)
        rect = cv2.minAreaRect(c)
        w, h = rect[1]
        if w > 0 and h > 0:
            width_px = max(w, h)
            return REF_DIMS["ean_13"]["width_mm"] / width_px
        return None

    return None


def measure_ink_extent(
    image: np.ndarray, ref_image: np.ndarray | None, ref_type: str | None
) -> MeasurementResult:
    """Measure the true ink extent (height) of a cropped numeral image.
    Uses reference object detection for calibration.
    """
    if ref_image is None or ref_type is None:
        return MeasurementRefusal(reason="Missing reference object image or type for calibration.")

    mm_per_pixel = detect_reference_object(ref_image, ref_type)
    if mm_per_pixel is None:
        return MeasurementRefusal(reason=f"Failed to detect reference object of type: {ref_type}.")

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

    # We assume a base ±5% confidence interval for estimated homography
    confidence = height_mm * 0.05

    return MeasurementCalibrated(
        value=height_mm, confidence_interval=confidence, unit="mm", reference_object=ref_type
    )


def calculate_pdp_area(
    image: np.ndarray,
    ref_image: np.ndarray | None,
    ref_type: str | None,
    shape: PackageShape,
    planarity_score: float = 1.0,
) -> MeasurementResult:
    """Calculate the Principal Display Panel (PDP) area in cm² according to Rule 7(4)."""
    if ref_image is None or ref_type is None:
        return MeasurementRefusal(reason="Missing reference object image or type for calibration.")

    mm_per_pixel = detect_reference_object(ref_image, ref_type)
    if mm_per_pixel is None:
        return MeasurementRefusal(reason=f"Failed to detect reference object of type: {ref_type}.")

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

    # Confidence interval approx ±10% for area
    confidence = area_cm2 * 0.10

    return MeasurementCalibrated(
        value=area_cm2,
        confidence_interval=confidence,
        unit="cm²",
        reference_object=ref_type,
        rule_limb=rule_limb,
    )
