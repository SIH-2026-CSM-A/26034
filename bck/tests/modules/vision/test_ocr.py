import socket
from unittest.mock import patch

import numpy as np
import pytest

from app.contracts import EvidenceProvider
from app.modules.vision.ocr import arbitrate_mrp, extract_mrp_quantity, extract_panel_text


@patch("pytesseract.image_to_string")
def test_extract_mrp_quantity_mocked(mock_tesseract, tmp_path):
    """Mocked test for Tesseract MRP extraction to ensure safe execution in headless CI."""
    mock_tesseract.return_value = "Rs 150"
    dummy_tess = tmp_path / "tessdata"
    dummy_tess.mkdir()

    img = np.full((100, 300, 3), 255, dtype=np.uint8)
    result = extract_mrp_quantity(img, tessdata_dir=str(dummy_tess))

    assert "150" in result
    assert "Rs" in result


@patch("paddleocr.PaddleOCR")
def test_extract_panel_text_mocked(mock_paddle, tmp_path):
    """Ensure PaddleOCR provider integrates cleanly and returns proper Contract models."""
    mock_instance = mock_paddle.return_value
    mock_instance.ocr.return_value = [[([[0, 0], [10, 0], [10, 10], [0, 10]], ("50g", 0.98))]]

    dummy_det = tmp_path / "det"
    dummy_det.mkdir()
    dummy_rec = tmp_path / "rec"
    dummy_rec.mkdir()

    img = np.zeros((10, 10, 3), dtype=np.uint8)
    spans = extract_panel_text(
        img,
        text_detection_model_dir=str(dummy_det),
        text_recognition_model_dir=str(dummy_rec),
    )

    assert len(spans) == 1
    assert spans[0].text == "50g"
    assert spans[0].confidence == 0.98
    assert spans[0].source_provider == EvidenceProvider.PADDLEOCR
    assert spans[0].span_id is not None
    assert spans[0].region_id == "panel"


@patch("paddleocr.PaddleOCR")
def test_ocr_network_isolation(mock_paddle, monkeypatch, tmp_path):
    """Network Isolation: Must not make any outbound connections."""

    def mock_socket_init(*args, **kwargs):
        raise OSError("Network call blocked by test constraint")

    monkeypatch.setattr(socket, "socket", mock_socket_init)

    dummy_det = tmp_path / "det"
    dummy_det.mkdir()
    dummy_rec = tmp_path / "rec"
    dummy_rec.mkdir()

    img = np.zeros((10, 10, 3), dtype=np.uint8)

    # This should pass without raising the mock_socket_init OSError
    spans = extract_panel_text(
        img,
        text_detection_model_dir=str(dummy_det),
        text_recognition_model_dir=str(dummy_rec),
    )
    assert isinstance(spans, list)


def test_offline_guarantee_raises_on_missing_tessdata():
    """
    Offline Guarantee: Missing local Tesseract data must raise FileNotFoundError,
    not silently fallback.
    """
    img = np.zeros((10, 10, 3), dtype=np.uint8)
    with pytest.raises(FileNotFoundError):
        extract_mrp_quantity(img, tessdata_dir="/invalid/path/that/does/not/exist")


def test_arbitration_disagreement_emits_review_marker():
    """
    Arbitration: Disagreement on MRP must return both readings and a review marker,
    not pick a winner.
    """
    # 1. Disagreement case (e.g., 8/B or 5/S confusion)
    result_disagree = arbitrate_mrp("150", "1S0")
    assert result_disagree.needs_review is True
    assert result_disagree.agreed_text is None
    assert result_disagree.primary_text == "150"
    assert result_disagree.secondary_text == "1S0"

    # 2. Agreement case
    result_agree = arbitrate_mrp("150", "150")
    assert result_agree.needs_review is False
    assert result_agree.agreed_text == "150"
