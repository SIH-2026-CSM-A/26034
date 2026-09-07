from pathlib import Path
from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pytest

from app.modules.vision.pdp import DetectionResult, detect_pdp


@pytest.fixture
def mock_pdp_model_file(tmp_path: Path) -> str:
    """Fixture providing a valid local file path for PDP weights."""
    weights_path = tmp_path / "pdp_detector.pt"
    weights_path.write_bytes(b"mock_binary_pdp_weights")
    return str(weights_path)


def test_detect_pdp_unset_weights_raises_runtime_error(monkeypatch: pytest.MonkeyPatch):
    """If weights_path is unset, missing, or empty, explicitly raises RuntimeError."""
    monkeypatch.delenv("PDP_WEIGHTS_PATH", raising=False)
    img = np.zeros((100, 100, 3), dtype=np.uint8)

    with pytest.raises(
        RuntimeError,
        match="PDP_WEIGHTS_PATH is unset. Cannot execute PDP detection without calibrated weights.",
    ):
        detect_pdp(img)

    with pytest.raises(
        RuntimeError,
        match="PDP_WEIGHTS_PATH is unset. Cannot execute PDP detection without calibrated weights.",
    ):
        detect_pdp(img, weights_path="")

    with pytest.raises(
        RuntimeError,
        match="PDP_WEIGHTS_PATH is unset. Cannot execute PDP detection without calibrated weights.",
    ):
        detect_pdp(img, weights_path="non_existent_weights_file.pt")


def test_detect_pdp_empty_image(mock_pdp_model_file: str):
    empty_img = np.array([])
    res = detect_pdp(empty_img, weights_path=mock_pdp_model_file)
    assert res.bbox == (0, 0, 0, 0)
    assert res.area == 0
    assert res.confidence == 0.0


@patch("ultralytics.YOLO")
def test_detect_pdp_success(mock_yolo_cls: MagicMock, mock_pdp_model_file: str):
    img = np.zeros((200, 200, 3), dtype=np.uint8)

    mock_boxes = MagicMock()
    mock_boxes.__len__.return_value = 1
    mock_boxes.conf.argmax.return_value = 0
    mock_boxes.conf.__getitem__.return_value.cpu().numpy.return_value = 0.95
    mock_boxes.xyxy.__getitem__.return_value.cpu().numpy.return_value = np.array([20, 30, 120, 150])

    mock_results = [MagicMock()]
    mock_results[0].boxes = mock_boxes

    mock_model_instance = MagicMock()
    mock_model_instance.return_value = mock_results
    mock_yolo_cls.return_value = mock_model_instance

    res = detect_pdp(img, weights_path=mock_pdp_model_file)

    assert isinstance(res, DetectionResult)
    assert res.bbox == (20, 30, 100, 120)
    assert res.area == 12000
    assert res.confidence == 0.95


@patch("ultralytics.YOLO")
def test_detect_pdp_no_detection_falls_back_to_full_image(
    mock_yolo_cls: MagicMock, mock_pdp_model_file: str
):
    img = np.zeros((80, 120, 3), dtype=np.uint8)

    mock_boxes = MagicMock()
    mock_boxes.__len__.return_value = 0

    mock_results = [MagicMock()]
    mock_results[0].boxes = mock_boxes

    mock_model_instance = MagicMock()
    mock_model_instance.return_value = mock_results
    mock_yolo_cls.return_value = mock_model_instance

    res = detect_pdp(img, weights_path=mock_pdp_model_file)

    assert res.bbox == (0, 0, 120, 80)
    assert res.area == 9600
    assert res.confidence == 0.0


def test_pdp_detector_different_boxes(mock_pdp_model_file: str):
    """Detector returns different bounding boxes for varying package inputs."""

    def mock_call(image, **kwargs):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        x, y, w, h = cv2.boundingRect(gray)

        mock_boxes = MagicMock()
        mock_boxes.__len__.return_value = 1
        mock_boxes.conf.argmax.return_value = 0
        mock_boxes.conf.__getitem__.return_value.cpu().numpy.return_value = 0.95
        mock_boxes.xyxy.__getitem__.return_value.cpu().numpy.return_value = np.array(
            [x, y, x + w, y + h]
        )

        mock_result = MagicMock()
        mock_result.boxes = mock_boxes
        return [mock_result]

    with patch("ultralytics.YOLO") as mock_yolo_cls:
        mock_instance = MagicMock()
        mock_instance.side_effect = mock_call
        mock_yolo_cls.return_value = mock_instance

        img1 = np.zeros((100, 100, 3), dtype=np.uint8)
        cv2.rectangle(img1, (10, 10), (40, 40), (255, 255, 255), -1)
        res1 = detect_pdp(img1, weights_path=mock_pdp_model_file)

        img2 = np.zeros((100, 100, 3), dtype=np.uint8)
        cv2.rectangle(img2, (60, 60), (90, 90), (255, 255, 255), -1)
        res2 = detect_pdp(img2, weights_path=mock_pdp_model_file)

        assert res1.bbox != res2.bbox
