import cv2
import numpy as np

from bck.app.modules.vision.preprocess import (
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
    h, w = 100, 100
    straight = np.zeros((h, w, 3), dtype=np.uint8)
    for x in range(10, w - 10, 20):
        straight[:, x : x + 4] = [255, 255, 255]

    center_x = (w - 1) / 2.0
    radius = w / 2.0
    x_indices = np.arange(w, dtype=np.float32)
    norm_x = np.clip((x_indices - center_x) / radius, -0.99, 0.99)
    x_forward = center_x + radius * (2.0 / np.pi) * np.arcsin(norm_x)
    map_x_fw = np.tile(x_forward.astype(np.float32), (h, 1))
    map_y_fw = np.tile(np.arange(h, dtype=np.float32)[:, None], (1, w))
    warped = cv2.remap(straight, map_x_fw, map_y_fw, cv2.INTER_LINEAR, cv2.BORDER_CONSTANT)

    unwarped = remap_curvature(warped)
    assert unwarped.shape == straight.shape

    # Assert straightness recovery: unwarped column variance across rows is below threshold
    row_variance = float(np.mean(np.var(unwarped.astype(float), axis=0)))
    assert row_variance < STRAIGHTNESS_VARIANCE_THRESHOLD


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
