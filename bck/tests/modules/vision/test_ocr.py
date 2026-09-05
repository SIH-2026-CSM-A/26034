from unittest.mock import patch

import cv2
import numpy as np

from app.modules.vision.ocr import extract_mrp_quantity, extract_panel_text


def test_extract_mrp_quantity_real_render():
    """
    AC2: Asserts against ACTUAL expected substrings from a REAL rendered test image.
    """
    img = np.full((100, 300, 3), 255, dtype=np.uint8)
    # Using characters strictly from the whitelist
    cv2.putText(img, "Rs 150", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 2)

    result = extract_mrp_quantity(img)

    assert "150" in result
    assert "Rs" in result


@patch("paddleocr.PaddleOCR")
def test_extract_panel_text_mocked(mock_paddle, tmp_path):
    """
    Ensure PaddleOCR provider integrates cleanly.
    """
    mock_instance = mock_paddle.return_value
    mock_instance.ocr.return_value = [[([[0, 0], [10, 0], [10, 10], [0, 10]], ("50g", 0.98))]]

    # Create real temporary directories so os.path.isdir passes naturally
    dummy_det = tmp_path / "det"
    dummy_det.mkdir()
    dummy_rec = tmp_path / "rec"
    dummy_rec.mkdir()

    img = np.zeros((10, 10, 3), dtype=np.uint8)
    spans = extract_panel_text(img, det_model_dir=str(dummy_det), rec_model_dir=str(dummy_rec))

    assert len(spans) == 1
    assert spans[0].text == "50g"
    assert spans[0].confidence == 0.98
