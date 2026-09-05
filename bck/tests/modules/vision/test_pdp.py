from unittest.mock import MagicMock, patch

import cv2
import numpy as np

from app.modules.vision.pdp import detect_pdp


@patch("ultralytics.YOLO")
def test_pdp_detector_different_boxes(mock_yolo_class, tmp_path):
    """
    AC1: Detector must return DIFFERENT bounding boxes for varying package inputs.
    """

    def mock_call(image, **kwargs):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        x, y, w, h = cv2.boundingRect(gray)

        # Fix: Explicitly declare length so the detector doesn't fallback to the full image
        mock_boxes = MagicMock()
        mock_boxes.__len__.return_value = 1

        # Fix: Deeply mock the PyTorch tensor chain (.cpu().numpy())
        mock_boxes.conf.argmax.return_value = 0

        conf_tensor = MagicMock()
        conf_tensor.cpu.return_value.numpy.return_value = 0.95
        mock_boxes.conf.__getitem__.return_value = conf_tensor

        xyxy_tensor = MagicMock()
        xyxy_tensor.cpu.return_value.numpy.return_value = np.array([x, y, x + w, y + h])
        mock_boxes.xyxy.__getitem__.return_value = xyxy_tensor

        mock_result = MagicMock()
        mock_result.boxes = mock_boxes
        return [mock_result]

    mock_instance = MagicMock()
    mock_instance.side_effect = mock_call
    mock_yolo_class.return_value = mock_instance

    # Use tmp_path to create a real dummy file so os.path.exists passes naturally
    dummy_model = tmp_path / "dummy.pt"
    dummy_model.touch()
    weights_path = str(dummy_model)

    img1 = np.zeros((100, 100, 3), dtype=np.uint8)
    cv2.rectangle(img1, (10, 10), (40, 40), (255, 255, 255), -1)
    res1 = detect_pdp(img1, weights_path=weights_path)

    img2 = np.zeros((100, 100, 3), dtype=np.uint8)
    cv2.rectangle(img2, (60, 60), (90, 90), (255, 255, 255), -1)
    res2 = detect_pdp(img2, weights_path=weights_path)

    img3 = np.zeros((100, 100, 3), dtype=np.uint8)
    cv2.rectangle(img3, (20, 40), (80, 60), (255, 255, 255), -1)
    res3 = detect_pdp(img3, weights_path=weights_path)

    assert res1.bbox != res2.bbox
    assert res2.bbox != res3.bbox
    assert res1.bbox != res3.bbox
