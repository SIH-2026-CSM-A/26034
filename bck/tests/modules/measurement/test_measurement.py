import cv2
import numpy as np
import pytest
from pydantic import ValidationError

from app.modules.measurement.schemas import (
    MeasurementCalibrated,
    MeasurementExact,
    MeasurementRefusal,
    PackageShape,
)
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
