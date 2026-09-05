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

    # CYLINDRICAL: 0.40 * (100 * (np.pi * 150))
    res_cyl = calculate_pdp_area(pdp_image, ref_image, "coin_10", PackageShape.CYLINDRICAL)
    expected_cyl_cm2 = (0.40 * (100.0 * (np.pi * 150.0))) / 100.0
    assert np.isclose(res_cyl.value, expected_cyl_cm2, rtol=0.10)

    # OTHER: 0.40 * (100 * 150)
    res_other = calculate_pdp_area(pdp_image, ref_image, "coin_10", PackageShape.OTHER)
    expected_other_cm2 = (0.40 * (100.0 * 150.0)) / 100.0
    assert np.isclose(res_other.value, expected_other_cm2, rtol=0.10)
