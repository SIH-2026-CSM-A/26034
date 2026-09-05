from unittest.mock import patch

import numpy as np

from app.modules.vision.ocr import extract_mrp_quantity, extract_panel_text


@patch("pytesseract.image_to_string")
def test_extract_mrp_quantity_mocked(mock_tesseract):
    """
    Mocked test for Tesseract MRP extraction to ensure safe execution in headless CI.
    """
    mock_tesseract.return_value = "Rs 150"

    img = np.full((100, 300, 3), 255, dtype=np.uint8)
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

    dummy_det = tmp_path / "det"
    dummy_det.mkdir()
    dummy_rec = tmp_path / "rec"
    dummy_rec.mkdir()

    img = np.zeros((10, 10, 3), dtype=np.uint8)
    spans = extract_panel_text(img, det_model_dir=str(dummy_det), rec_model_dir=str(dummy_rec))

    assert len(spans) == 1
    assert spans[0].text == "50g"
    assert spans[0].confidence == 0.98
