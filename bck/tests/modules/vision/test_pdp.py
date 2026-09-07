from pathlib import Path
from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pytest

from app.modules.vision.pdp import PDPResult, detect_pdp


@pytest.fixture
def mock_pdp_model_file(tmp_path: Path) -> str:
    """Fixture providing a valid local file path for PDP weights."""
    weights_path = tmp_path / "pdp_detector.pt"
    weights_path.write_bytes(b"mock_binary_pdp_weights")
    return str(weights_path)


def test_detect_pdp_unset_or_missing_model_path():
    img = np.zeros((100, 100, 3), dtype=np.uint8)

    # Empty string model_path
    res_empty = detect_pdp(img, model_path="")
    assert res_empty.bounding_box == (0, 0, 100, 100)
    assert res_empty.confidence == 0.0

    # None model_path
    res_none = detect_pdp(img, model_path=None)
    assert res_none.bounding_box == (0, 0, 100, 100)
    assert res_none.confidence == 0.0

    # Non-existent file path
    res_nonexistent = detect_pdp(img, model_path="non_existent_weights_file.pt")
    assert res_nonexistent.bounding_box == (0, 0, 100, 100)
    assert res_nonexistent.confidence == 0.0


def test_detect_pdp_default_weights_path_unset_env(monkeypatch: pytest.MonkeyPatch):
    """Calling detect_pdp(img) without weights_path falls through gracefully."""
    monkeypatch.delenv("PDP_WEIGHTS_PATH", raising=False)
    img = np.zeros((120, 120, 3), dtype=np.uint8)
    res = detect_pdp(img)
    assert res.bounding_box == (0, 0, 120, 120)
    assert res.confidence == 0.0


def test_detect_pdp_image_path_string(tmp_path: Path):
    """Passing image path string to detect_pdp reads image and works seamlessly."""
    img_file = tmp_path / "sample_package.png"
    img = np.zeros((150, 200, 3), dtype=np.uint8)
    cv2.imwrite(str(img_file), img)

    res = detect_pdp(str(img_file), weights_path=None)
    assert res.bounding_box == (0, 0, 200, 150)
    assert res.confidence == 0.0


def test_detect_pdp_empty_image(mock_pdp_model_file: str):
    empty_img = np.array([])
    with pytest.raises(ValueError, match="Input image for PDP detection cannot be empty"):
        detect_pdp(empty_img, model_path=mock_pdp_model_file)


@patch("ultralytics.YOLO")
def test_detect_pdp_success(mock_yolo_cls: MagicMock, mock_pdp_model_file: str):
    img = np.zeros((200, 200, 3), dtype=np.uint8)

    mock_box = MagicMock()
    mock_box.conf = [0.95]
    mock_box.xyxy = [MagicMock()]
    mock_box.xyxy[0].cpu().numpy().astype.return_value = np.array([20, 30, 120, 150])

    mock_results = [MagicMock()]
    mock_results[0].boxes = [mock_box]

    mock_model_instance = MagicMock()
    mock_model_instance.predict.return_value = mock_results
    mock_yolo_cls.return_value = mock_model_instance

    res = detect_pdp(img, model_path=mock_pdp_model_file, confidence_threshold=0.5)

    assert isinstance(res, PDPResult)
    assert res.bounding_box == (20, 30, 100, 120)
    assert res.confidence == 0.95
    assert res.area_cm2 > 0.0
    assert res.cropped_image.shape == (120, 100, 3)
