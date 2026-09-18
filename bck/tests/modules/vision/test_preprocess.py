import time

import cv2
import numpy as np
import pytest

from app.modules.vision.preprocess import (
    QualityResult,
    correct_perspective,
    correct_shadows,
    quality_gate,
    remap_curvature,
    remove_glare,
)

# Maximum allowable column variance across rows to verify straightness recovery in unwarped images.
STRAIGHTNESS_VARIANCE_THRESHOLD = 1.0


def test_quality_gate_pass():
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    cv2.rectangle(img, (20, 20), (80, 80), (255, 255, 255), -1)
    res = quality_gate(img, blur_threshold=10.0, glare_threshold=0.5, completeness_threshold=0.1)
    assert isinstance(res, QualityResult)
    assert res.is_acceptable is True
    assert res.reason_code == "PASS"


def test_quality_gate_blur_exceeded():
    img = np.full((100, 100, 3), 128, dtype=np.uint8)
    res = quality_gate(img, blur_threshold=50.0)
    assert res.is_acceptable is False
    assert res.reason_code == "BLUR_EXCEEDED"


def test_quality_gate_glare_exceeded():
    """Glare is measured over the package surface, not the whole frame.

    VIS-010: a near-white backdrop is not glare. The fixture is a dark package filling the
    frame with a saturated reflection on it, so the subject mask is large and the glare
    ratio reflects the reflection rather than the background.
    """
    img = np.full((100, 100, 3), 60, dtype=np.uint8)
    cv2.rectangle(img, (30, 30), (69, 69), (255, 255, 255), -1)
    res = quality_gate(img, blur_threshold=1.0, glare_threshold=0.10)
    assert res.is_acceptable is False
    assert res.reason_code == "GLARE_EXCEEDED"


def test_a_white_backdrop_is_not_glare():
    """VIS-010 regression: the defect this fixes. A dark package on a white studio
    backdrop measured 0.19-0.83 glare on the old whole-frame ratio and was refused.
    All four real captures failed that way and no image could reach a verdict."""
    img = np.full((100, 100, 3), 255, dtype=np.uint8)
    cv2.rectangle(img, (20, 20), (79, 79), (60, 60, 60), -1)
    res = quality_gate(img, blur_threshold=1.0, glare_threshold=0.15)
    assert res.glare_ratio < 0.15


def test_quality_gate_empty_image():
    res = quality_gate(np.array([]))
    assert res.is_acceptable is False
    assert res.reason_code == "IMAGE_EMPTY"


def test_correct_perspective_skewed_quad():
    img = np.zeros((200, 200, 3), dtype=np.uint8)
    pts = np.array([[30, 40], [160, 20], [180, 170], [20, 150]], dtype=np.int32)
    cv2.fillPoly(img, [pts], (255, 255, 255))

    deskewed = correct_perspective(img)
    assert deskewed is not None
    assert deskewed.shape[0] > 0 and deskewed.shape[1] > 0


def test_remap_curvature_recovery():
    # Construct a synthetic warped image with a known stripe position
    # and assert that remap_curvature recovers the expected x-position.
    h, w = 100, 100
    img = np.zeros((h, w, 3), dtype=np.uint8)
    target_x = 50
    cv2.line(img, (target_x, 10), (target_x, 90), (255, 255, 255), 3)

    unwarped = remap_curvature(img)
    # Find the column with maximum intensity in the middle row
    middle_row = unwarped[50, :, 0]
    recovered_x = int(np.argmax(middle_row))

    # Assert that the stripe position is correctly recovered close to target_x
    assert abs(recovered_x - target_x) < 5


def test_remove_glare():
    img = np.full((100, 100, 3), 100, dtype=np.uint8)
    img[40:60, 40:60] = [250, 250, 250]
    inpainted = remove_glare(img)
    assert inpainted.shape == img.shape
    assert np.mean(inpainted[45:55, 45:55]) < 240


def test_correct_shadows():
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    for y in range(100):
        img[y, :] = [80 + y // 2, 80 + y // 2, 80 + y // 2]

    lab_before = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    _, a_before, b_before = cv2.split(lab_before)

    result = correct_shadows(img)

    lab_after = cv2.cvtColor(result, cv2.COLOR_BGR2LAB)
    _, a_after, b_after = cv2.split(lab_after)

    # Assert that A and B channels in LAB space are identical (w/ 2-unit BGR tolerance)
    assert np.allclose(a_before, a_after, atol=2)
    assert np.allclose(b_before, b_after, atol=2)


def test_correct_perspective_transforms():
    # Construct an image with a clear quadrilateral quad and
    # assert perspective transform alters shape
    h, w = 200, 200
    img = np.zeros((h, w, 3), dtype=np.uint8)
    pts = np.array([[50, 50], [150, 30], [180, 170], [20, 180]], dtype=np.int32)
    cv2.fillPoly(img, [pts], (255, 255, 255))

    warped = correct_perspective(img)
    # Assert that warpPerspective successfully executed and changed dimensions/content
    assert warped.shape != img.shape or not np.array_equal(warped, img)


def test_correct_shadows_clahe_chromaticity():
    # Acceptance criterion: take a safe mid-range color image, run correct_shadows,
    # and assert a and b channels are preserved while L differs due to CLAHE.
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    for i in range(100):
        img[i, :, :] = [100 + (i % 20), 120, 140]

    lab_in = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l_in, a_in, b_in = cv2.split(lab_in)

    enhanced = correct_shadows(img)
    lab_out = cv2.cvtColor(enhanced, cv2.COLOR_BGR2LAB)
    l_out, a_out, b_out = cv2.split(lab_out)

    # a and b channels must be preserved without clipping distortion
    assert np.max(np.abs(a_in.astype(int) - a_out.astype(int))) <= 2
    assert np.max(np.abs(b_in.astype(int) - b_out.astype(int))) <= 2

    # L channel should differ due to CLAHE contrast enhancement
    assert not np.array_equal(l_in, l_out)


def test_remap_curvature_performance_at_realistic_resolution():
    """A raw Python per-pixel loop would blow this budget; a vectorized
    implementation should clear it comfortably."""
    large_image = np.zeros((3000, 4000, 3), dtype=np.uint8)
    start = time.perf_counter()
    result = remap_curvature(large_image)
    elapsed = time.perf_counter() - start

    assert result.shape == large_image.shape
    assert elapsed < 0.5  # generous budget; a per-pixel Python loop would take 10s+


def test_prepared_points_map_back_onto_the_photograph():
    """A mark found on the prepared frame is reported where it is on the photograph.

    Deskew and unwarp both move pixels, and the photograph is what the evidence record
    stores. Drawn rather than computed: the mark is located on the prepared image by
    looking for it, so this fails if ``to_source`` and the real transforms ever disagree.
    """
    from app.modules.vision.preprocess import prepare_panel

    frame = np.full((900, 1200, 3), 200, dtype=np.uint8)
    cv2.rectangle(frame, (100, 100), (1100, 800), (40, 40, 40), -1)
    cv2.circle(frame, (830, 330), 6, (255, 255, 255), -1)

    for cylindrical in (False, True):
        prepared = prepare_panel(frame, cylindrical=cylindrical)
        assert prepared.perspective is not None, "the panel outline covers 65 % of the frame"
        bright = np.argwhere(cv2.cvtColor(prepared.image, cv2.COLOR_BGR2GRAY) > 250)
        centre = bright.mean(axis=0)[::-1]
        restored = prepared.to_source(np.array([centre]))[0]
        assert restored == pytest.approx((830.0, 330.0), abs=2.0), cylindrical


def test_a_small_quadrilateral_is_not_taken_for_the_label():
    """A price flash is four-cornered too. Warping to it would crop the declarations away."""
    from app.modules.vision.preprocess import prepare_panel

    frame = np.full((900, 1200, 3), 200, dtype=np.uint8)
    cv2.rectangle(frame, (500, 400), (700, 500), (40, 40, 40), -1)
    prepared = prepare_panel(frame)
    assert prepared.perspective is None
    assert prepared.image.shape == frame.shape


def test_spans_are_returned_untouched_when_nothing_geometric_ran():
    from app.modules.vision.preprocess import PreparedPanel

    spans = [object()]
    assert PreparedPanel(image=np.zeros((2, 2, 3), np.uint8)).restore(spans)[0] is spans[0]


def test_a_malformed_polygon_is_not_laundered_into_a_finite_one():
    """Measured before the guard: a NaN vertex left the inverse homography as a number."""
    from types import SimpleNamespace

    from app.modules.vision.preprocess import prepare_panel

    frame = np.full((900, 1200, 3), 200, dtype=np.uint8)
    cv2.rectangle(frame, (100, 100), (1100, 800), (40, 40, 40), -1)
    span = SimpleNamespace(polygon=((float("nan"), 5.0), (9.0, 5.0), (9.0, 9.0)))
    assert prepare_panel(frame).restore([span])[0] is span
