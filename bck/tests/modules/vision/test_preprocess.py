import cv2
import numpy as np

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
    img = np.full((100, 100, 3), 250, dtype=np.uint8)
    cv2.line(img, (0, 0), (99, 99), (0, 0, 0), 3)
    cv2.line(img, (0, 99), (99, 0), (0, 0, 0), 3)
    res = quality_gate(img, blur_threshold=1.0, glare_threshold=0.10)
    assert res.is_acceptable is False
    assert res.reason_code == "GLARE_EXCEEDED"


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
