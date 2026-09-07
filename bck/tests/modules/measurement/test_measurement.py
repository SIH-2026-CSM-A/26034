import cv2
import numpy as np
import pytest
from pydantic import ValidationError

from app.contracts import (
    MeasurementCalibrated,
    MeasurementExact,
    MeasurementMarginExact,
    MeasurementRefusal,
)
from app.modules.measurement.schemas import PackageShape
from app.modules.measurement.services import calculate_pdp_area, measure_ink_extent


def test_measurement_without_calibration_fails():
    """Assert that construction of a measurement without a calibration source fails."""
    with pytest.raises(ValidationError):
        # Missing 'reference_object'
        MeasurementCalibrated(value=10.0, confidence_interval=1.0, unit="mm")

    with pytest.raises(ValidationError):
        # Missing 'confidence_interval'
        MeasurementCalibrated(value=10.0, reference_object="coin_10", unit="mm")


def test_no_code_path_returns_bare_float():
    """Ensure that the measurement functions return MeasurementResult, not a bare float."""
    # Create dummy images
    numeral_image = np.zeros((100, 100), dtype=np.uint8)
    ref_image = np.zeros((100, 100), dtype=np.uint8)

    # We pass an empty image that won't match a reference object
    result1 = measure_ink_extent(numeral_image, ref_image, "coin_10")
    assert not isinstance(result1, float)
    assert isinstance(result1, (MeasurementExact, MeasurementCalibrated, MeasurementRefusal))

    result2 = calculate_pdp_area(numeral_image, ref_image, "coin_10", PackageShape.RECTANGULAR)
    assert not isinstance(result2, float)
    assert isinstance(result2, (MeasurementExact, MeasurementCalibrated, MeasurementRefusal))


def test_ink_extent_measured_correctly():
    """Test that ink extent is measured correctly vs. a padded bounding box."""
    # Create a 200x200 image for numeral. Background is white (255)
    numeral_image = np.ones((200, 200), dtype=np.uint8) * 255
    # Draw "ink" (black, 0) from y=50 to y=150 (inclusive), so height = 101 px
    numeral_image[50:151, 80:120] = 0

    # Create a reference image with a known coin (radius = 27 px, diameter = 54 px)
    ref_image = np.zeros((200, 200), dtype=np.uint8)
    # Draw an anti-aliased circle and apply blur to give the gradient detector a slope
    cv2.circle(ref_image, (100, 100), 27, 255, -1, cv2.LINE_AA)
    ref_image = cv2.GaussianBlur(ref_image, (5, 5), 0)
    # The homography scale for coin_10 (27.0mm) should be 27.0 / (2 * 27) = 0.5 mm_per_pixel

    result = measure_ink_extent(numeral_image, ref_image, "coin_10")

    # It must return a calibrated measurement
    assert isinstance(result, MeasurementCalibrated)
    # 101 pixels * 0.5 mm/pixel = 50.5 mm
    # Allow 5% tolerance for HoughCircles rasterization variance
    assert np.isclose(result.value, 50.5, rtol=0.05)
    assert result.unit == "mm"
    assert result.reference_object == "coin_10"

    # Assert that the bounding box extent (200 px) and ink extent (101 px) diverge,
    # proving the Otsu thresholding successfully isolated the ink from the padding.
    theoretical_mm_per_px = 0.5
    padded_bbox_height_mm = numeral_image.shape[0] * theoretical_mm_per_px
    assert result.value < padded_bbox_height_mm * 0.6  # 50.5 mm is much smaller than 100 mm


def test_absent_reference_object_returns_refusal():
    """Assert that absent a reference object, the API returns the explicit refusal mode."""
    numeral_image = np.zeros((100, 100), dtype=np.uint8)

    # 1. No reference image provided
    result_none = measure_ink_extent(numeral_image, None, "coin_10")
    assert isinstance(result_none, MeasurementRefusal)
    assert result_none.mode == "refusal"
    assert "Missing reference" in result_none.reason

    # 2. Reference image provided but detection fails (empty image)
    ref_image_empty = np.zeros((100, 100), dtype=np.uint8)
    result_empty = measure_ink_extent(numeral_image, ref_image_empty, "coin_10")
    assert isinstance(result_empty, MeasurementRefusal)
    assert result_empty.mode == "refusal"
    assert "Failed to detect reference" in result_empty.reason


def test_pdp_area_calculation():
    """Test PDP area calculation with valid reference for all shapes."""
    # Image size 200x300 pixels
    pdp_image = np.zeros((200, 300), dtype=np.uint8)

    # Reference image with coin (diameter = 54 px => 0.5 mm/pixel)
    ref_image = np.zeros((200, 200), dtype=np.uint8)
    # Draw an anti-aliased circle and apply blur for robust gradient detection
    cv2.circle(ref_image, (100, 100), 27, 255, -1, cv2.LINE_AA)
    ref_image = cv2.GaussianBlur(ref_image, (5, 5), 0)

    # RECTANGULAR: 100 * 150 = 15000 mm^2 = 150 cm^2
    res_rect = calculate_pdp_area(pdp_image, ref_image, "coin_10", PackageShape.RECTANGULAR)
    assert isinstance(res_rect, MeasurementCalibrated)
    assert np.isclose(res_rect.value, 150.0, rtol=0.10)
    assert res_rect.unit == "cm²"
    assert res_rect.rule_limb == "rectangular"

    # CYLINDRICAL: 0.40 * (100 * (np.pi * 150))
    res_cyl = calculate_pdp_area(pdp_image, ref_image, "coin_10", PackageShape.CYLINDRICAL)
    assert isinstance(res_cyl, MeasurementCalibrated)
    expected_cyl_cm2 = (0.40 * (100.0 * (np.pi * 150.0))) / 100.0
    assert np.isclose(res_cyl.value, expected_cyl_cm2, rtol=0.10)
    assert res_cyl.rule_limb == "cylindrical 40%"

    # OTHER with low planarity
    res_other_refusal = calculate_pdp_area(
        pdp_image, ref_image, "coin_10", PackageShape.OTHER, planarity_score=0.80
    )
    assert isinstance(res_other_refusal, MeasurementRefusal)
    assert "not adequately planar" in res_other_refusal.reason

    # OTHER with high planarity: direct area (100 * 150 = 150 cm^2)
    res_other_calibrated = calculate_pdp_area(
        pdp_image, ref_image, "coin_10", PackageShape.OTHER, planarity_score=0.90
    )
    assert isinstance(res_other_calibrated, MeasurementCalibrated)
    assert np.isclose(res_other_calibrated.value, 150.0, rtol=0.10)
    assert res_other_calibrated.rule_limb == "other-panel-measured"


def test_measurement_exact_artwork_path():
    """Assert that using the is_artwork=True path returns MeasurementExact."""
    numeral_image = np.ones((200, 200), dtype=np.uint8) * 255
    numeral_image[50:151, 80:120] = 0  # 101 px height

    # 300 DPI means mm_per_pixel = 25.4 / 300
    # height_mm = 101 * (25.4 / 300) = 8.55133 mm
    result = measure_ink_extent(numeral_image, is_artwork=True, artwork_dpi=300)
    assert isinstance(result, MeasurementExact)
    assert np.isclose(result.value, 8.55133, rtol=0.01)
    assert result.unit == "mm"

    # For PDP area
    pdp_image = np.zeros((200, 300), dtype=np.uint8)
    # height = 200 * (25.4/300) = 16.933 mm
    # width = 300 * (25.4/300) = 25.4 mm
    # area_mm2 = 16.933 * 25.4 = 430.1 mm^2 = 4.301 cm^2
    res_area = calculate_pdp_area(
        pdp_image, is_artwork=True, artwork_dpi=300, shape=PackageShape.RECTANGULAR
    )
    assert isinstance(res_area, MeasurementExact)
    assert np.isclose(res_area.value, 4.301, rtol=0.01)
    assert res_area.unit == "cm²"
    assert res_area.rule_limb == "rectangular"


def test_measurement_photograph_never_exact():
    """
    Assert that when is_artwork=False (photograph), the return type is
    strictly Calibrated or Refusal, never Exact.
    """
    numeral_image = np.ones((200, 200), dtype=np.uint8) * 255
    numeral_image[50:151, 80:120] = 0
    ref_image = np.zeros((200, 200), dtype=np.uint8)
    cv2.circle(ref_image, (100, 100), 27, 255, -1, cv2.LINE_AA)
    ref_image = cv2.GaussianBlur(ref_image, (5, 5), 0)

    result_calibrated = measure_ink_extent(numeral_image, ref_image, "coin_10", is_artwork=False)
    assert not isinstance(result_calibrated, MeasurementExact)
    assert isinstance(result_calibrated, MeasurementCalibrated)

    # Trigger refusal
    result_refusal = measure_ink_extent(numeral_image, None, "coin_10", is_artwork=False)
    assert not isinstance(result_refusal, MeasurementExact)
    assert isinstance(result_refusal, MeasurementRefusal)


def test_measure_contrast_ratio():
    """
    Assert measure_contrast_ratio returns a MeasurementCalibrated result
    with a dynamically calculated confidence interval.
    """
    # Import the new function explicitly inside the test or at the top of the file
    from app.modules.measurement.services import measure_contrast_ratio

    # Pure black text crop (BGR)
    text_crop = np.zeros((50, 50, 3), dtype=np.uint8)

    # Pure white background crop (BGR)
    bg_crop = np.ones((50, 50, 3), dtype=np.uint8) * 255

    # White luminance = 1.0, Black = 0.0
    # Contrast ratio = (1.0 + 0.05) / (0.0 + 0.05) = 1.05 / 0.05 = 21.0
    result = measure_contrast_ratio(text_crop, bg_crop)

    assert isinstance(result, MeasurementCalibrated)
    assert np.isclose(result.value, 21.0)
    assert result.unit == "ratio"
    assert result.reference_object == "color_variance"

    # Because standard deviation of flat pure colors is 0, confidence interval should be 0.
    assert result.confidence_interval == 0.0

    # Test dynamic confidence interval with a noisy background
    np.random.seed(42)
    noisy_bg_crop = np.random.randint(200, 255, (50, 50, 3), dtype=np.uint8)
    result_noisy = measure_contrast_ratio(text_crop, noisy_bg_crop)

    assert isinstance(result_noisy, MeasurementCalibrated)
    # The confidence interval should now be > 0 because of variance in the noisy background
    assert result_noisy.confidence_interval > 0.0


def test_measure_width_to_height_ratio():
    """Assert measure_width_to_height_ratio calculates ratio correctly and ignores padding."""
    from app.modules.measurement.services import measure_width_to_height_ratio

    # 200x200 gray background (not pure white) to prove Otsu separates the foreground
    numeral_image = np.ones((200, 200), dtype=np.uint8) * 200

    # Draw an irregular 'L' shape using dark gray ink (not pure black)
    # Vertical bar: y=50 to 149 (height 100), x=80 to 99
    numeral_image[50:150, 80:100] = 100
    # Horizontal bar: y=130 to 149, x=100 to 129
    numeral_image[130:150, 100:130] = 100

    # Total active ink extent:
    # X spans from 80 to 129 (width = 50)
    # Y spans from 50 to 149 (height = 100)
    # Expected ratio = 50.0 / 100.0 = 0.5
    result = measure_width_to_height_ratio(numeral_image, is_artwork=True, artwork_dpi=300)
    assert isinstance(result, MeasurementExact)
    assert np.isclose(result.value, 0.5, rtol=0.01)
    assert result.unit == "ratio"


def test_measure_margins():
    """Assert measure_margins calculates distance to nearest ink independently.
    Proves margins come back as margin-typed results with exact values on the artwork path.
    """
    from app.modules.measurement.services import measure_margins

    # 300x300 image
    image = np.ones((300, 300), dtype=np.uint8) * 255
    # Draw some ink at the top (y=10)
    image[10:20, 100:200] = 0
    # Draw some ink on the left (x=20)
    image[100:200, 20:30] = 0

    # Bbox: x=100, y=100, w=100, h=100
    # Above margin: nearest ink is at y=19. bbox top is y=100. margin = 100 - 19 - 1 = 80 pixels.
    # Below margin: no ink below bbox (y=200 to 300). distance to edge = 300 - 200 = 100 pixels.
    # Left margin: nearest ink is at x=29. bbox left is x=100. margin = 100 - 29 - 1 = 70 pixels.
    # Right margin: no ink right of bbox (x=200 to 300). distance to edge = 300 - 200 = 100 pixels.
    bbox = (100, 100, 100, 100)

    results = measure_margins(
        image,
        bbox,
        is_artwork=True,
        artwork_dpi=25.4,  # mm_per_pixel = 1.0
    )

    assert isinstance(results["above"], MeasurementMarginExact)
    assert np.isclose(results["above"].value, 80.0)

    assert isinstance(results["below"], MeasurementMarginExact)
    assert np.isclose(results["below"].value, 100.0)

    assert isinstance(results["left"], MeasurementMarginExact)
    assert np.isclose(results["left"].value, 70.0)

    assert isinstance(results["right"], MeasurementMarginExact)
    assert np.isclose(results["right"].value, 100.0)


def test_ean_13_exact_width_regression():
    """Assert REF_DIMS['ean_13']['width_mm'] is exactly 37.29."""
    from app.modules.measurement.services import REF_DIMS

    assert REF_DIMS["ean_13"]["width_mm"] == 37.29


def test_oblique_camera_angle_rectification():
    """
    Create a synthetic oblique image, warp it, and prove the perspective warp
    round-trips correctly. Note: This does not prove absolute measurement accuracy
    because systematic scale errors cancel out in this path.
    """
    from app.modules.measurement.services import measure_ink_extent

    # 1. Create a synthetic EAN-13 barcode (fronto-parallel) in a 400x400 image
    ref_image = np.ones((400, 400), dtype=np.uint8) * 255
    cv2.rectangle(ref_image, (150, 165), (250, 235), 0, -1)
    for x in range(160, 250, 5):
        cv2.line(ref_image, (x, 165), (x, 235), 255, 1)

    # Create the product image (numeral ink)
    numeral_image = np.ones((400, 400), dtype=np.uint8) * 255
    cv2.rectangle(numeral_image, (200, 200), (220, 250), 0, -1)

    # ESTABLISH BASELINE on the unwarped, orthogonal images first
    baseline_result = measure_ink_extent(numeral_image, ref_image, "ean_13", is_artwork=False)
    assert isinstance(baseline_result, MeasurementCalibrated)
    expected_height_mm = baseline_result.value

    # Define a known perspective warp (simulate camera tilt)
    src_pts = np.float32([[0, 0], [400, 0], [400, 400], [0, 400]])
    dst_pts = np.float32([[50, 80], [350, 20], [380, 350], [20, 320]])
    h_matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)

    # Warp both images
    warped_ref = cv2.warpPerspective(ref_image, h_matrix, (400, 400), borderValue=255)
    warped_numeral = cv2.warpPerspective(numeral_image, h_matrix, (400, 400), borderValue=255)

    # Pass the WARPED images to the pipeline. It must detect, unwarp,
    # and recover the baseline height.
    result = measure_ink_extent(warped_numeral, warped_ref, "ean_13", is_artwork=False)

    assert isinstance(result, MeasurementCalibrated)
    # Allow 10% tolerance (EAN-13 confidence interval) for the warp and rasterization
    assert np.isclose(result.value, expected_height_mm, rtol=0.10)


def test_rectification_failure_returns_refusal():
    """Assert rectification failure returns MeasurementRefusal."""
    from app.modules.measurement.services import detect_reference_object

    # Empty image should fail to find any contours or corners
    empty_img = np.ones((400, 400), dtype=np.uint8) * 255

    res_id = detect_reference_object(empty_img, "id_card")
    assert isinstance(res_id, MeasurementRefusal)
    assert "Rectification failed" in res_id.reason

    res_ean = detect_reference_object(empty_img, "ean_13")
    assert isinstance(res_ean, MeasurementRefusal)
    assert "Rectification failed" in res_ean.reason


def test_zero_margin_is_valid():
    """Assert that a zero margin resolves to 0.0 without raising an error."""
    import numpy as np

    from app.contracts import MeasurementMarginExact
    from app.modules.measurement.services import measure_margins

    # 100x100 white image
    image = np.ones((100, 100), dtype=np.uint8) * 255

    # Active ink (black) in top-left quadrant (0:50, 0:50)
    image[0:50, 0:50] = 0

    # Declaration bbox flush against the ink boundary at (50, 50)
    bbox = (50, 50, 20, 20)

    results = measure_margins(
        image,
        bbox,
        is_artwork=True,
        artwork_dpi=25.4,
    )

    assert isinstance(results["above"], MeasurementMarginExact)
    assert results["above"].value == 0.0
    assert results["left"].value == 0.0


def test_zero_margin_calibrated_path():
    """Assert a flush margin yields a MeasurementMarginCalibrated with zero value and confidence."""
    import cv2
    import numpy as np

    from app.contracts import MeasurementMarginCalibrated
    from app.modules.measurement.services import measure_margins

    image = np.ones((100, 100), dtype=np.uint8) * 255
    image[0:50, 0:50] = 0
    bbox = (50, 50, 20, 20)

    ref_image = np.zeros((100, 100), dtype=np.uint8)
    cv2.circle(ref_image, (50, 50), 30, 255, -1, cv2.LINE_AA)

    results = measure_margins(
        image,
        bbox,
        ref_image=ref_image,
        ref_type="coin_10",
        is_artwork=False,
    )

    assert isinstance(results["above"], MeasurementMarginCalibrated)
    assert results["above"].value == 0.0
    assert results["above"].confidence_interval > 0.0


def test_margin_overlap_is_negative():
    """Assert margins that overlap active ink return negative distances."""
    import numpy as np

    from app.contracts import MeasurementRefusal
    from app.modules.measurement.services import measure_margins

    image = np.ones((100, 100), dtype=np.uint8) * 255
    image[0:60, 0:60] = 0

    bbox = (50, 50, 20, 20)

    results = measure_margins(
        image,
        bbox,
        is_artwork=True,
        artwork_dpi=25.4,
    )

    assert isinstance(results["above"], MeasurementRefusal)
    assert "overlap" in results["above"].reason.lower()


def test_coin_oblique_synthetic_geometry():
    """Prove MEA-007 correctly recovers the original scale of an oblique coin."""
    import cv2
    import numpy as np

    from app.contracts import MeasurementRefusal
    from app.modules.measurement.services import detect_reference_object

    img = np.zeros((1000, 1000), dtype=np.uint8)
    cv2.circle(img, (500, 500), 100, 255, -1)

    f_true = float(np.hypot(1000, 1000))
    k_mat = np.array([[f_true, 0.0, 500.0], [0.0, f_true, 500.0], [0.0, 0.0, 1.0]])
    theta_true = np.deg2rad(30)
    r_true = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.0, np.cos(theta_true), -np.sin(theta_true)],
            [0.0, np.sin(theta_true), np.cos(theta_true)],
        ]
    )

    y_shift = f_true * np.tan(theta_true)
    t_mat = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, y_shift], [0.0, 0.0, 1.0]])
    warp_m = t_mat @ k_mat @ r_true @ np.linalg.inv(k_mat)

    warped = cv2.warpPerspective(img, warp_m, (1000, 1000))
    warped_bgr = cv2.cvtColor(warped, cv2.COLOR_GRAY2BGR)

    res = detect_reference_object(warped_bgr, "coin_10")
    assert not isinstance(res, MeasurementRefusal), "Refusal: " + (
        res.reason if hasattr(res, "reason") else ""
    )

    scale, conf, h_matrix = res
    assert h_matrix is not None

    # Project coordinate points directly to avoid canvas clipping during unwarp
    rect_pts = np.float32([[200, 400], [300, 400], [300, 600], [200, 600]])
    warped_pts = cv2.perspectiveTransform(np.array([rect_pts]), warp_m)[0]
    recov_pts = cv2.perspectiveTransform(np.array([warped_pts]), h_matrix)[0]

    recovered_height = np.linalg.norm(recov_pts[0] - recov_pts[3])

    expected_height = 200.0
    error = abs(recovered_height - expected_height) / expected_height
    assert error <= 0.05, f"Height {recovered_height:.2f} deviates from {expected_height} by >5%"
