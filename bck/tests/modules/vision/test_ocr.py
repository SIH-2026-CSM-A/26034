import socket
import uuid
from unittest.mock import patch

import numpy as np
import pytest

from app.contracts import EvidenceProvider, ExtractedSpan
from app.modules.vision.ocr import (
    arbitrate_field_declaration,
    arbitrate_mrp,
    extract_mrp_quantity,
    extract_panel_text,
)


@patch("pytesseract.image_to_string")
def test_extract_mrp_quantity_mocked(mock_tesseract, tmp_path):
    mock_tesseract.return_value = "Rs 150"
    dummy_tess = tmp_path / "tessdata"
    dummy_tess.mkdir()
    img = np.full((100, 300, 3), 255, dtype=np.uint8)
    result = extract_mrp_quantity(img, tessdata_dir=str(dummy_tess))
    assert "150" in result
    assert "Rs" in result


@patch("paddleocr.PaddleOCR")
def test_extract_panel_text_mocked(mock_paddle, tmp_path):
    mock_instance = mock_paddle.return_value
    mock_instance.ocr.return_value = [[([[0, 0], [10, 0], [10, 10], [0, 10]], ("50g", 0.98))]]
    mock_instance.predict.return_value = [[([[0, 0], [10, 0], [10, 10], [0, 10]], ("50g", 0.98))]]
    dummy_det, dummy_rec = tmp_path / "det", tmp_path / "rec"
    dummy_det.mkdir()
    dummy_rec.mkdir()
    spans = extract_panel_text(
        np.zeros((10, 10, 3), dtype=np.uint8), str(dummy_det), str(dummy_rec)
    )
    assert spans[0].text == "50g"
    assert spans[0].source_provider == EvidenceProvider.PADDLEOCR


@patch("paddleocr.PaddleOCR")
def test_ocr_network_isolation(mock_paddle, monkeypatch, tmp_path):
    def mock_socket_init(*args, **kwargs):
        raise OSError("Network blocked")

    monkeypatch.setattr(socket, "socket", mock_socket_init)
    if hasattr(socket, "create_connection"):
        monkeypatch.setattr(socket, "create_connection", mock_socket_init)
    dummy_det, dummy_rec = tmp_path / "det", tmp_path / "rec"
    dummy_det.mkdir()
    dummy_rec.mkdir()
    spans = extract_panel_text(
        np.zeros((10, 10, 3), dtype=np.uint8), str(dummy_det), str(dummy_rec)
    )
    assert isinstance(spans, list)


def test_offline_guarantee_raises_on_missing_tessdata():
    with pytest.raises(FileNotFoundError):
        extract_mrp_quantity(np.zeros((10, 10, 3), dtype=np.uint8), "/invalid/path")


def test_arbitration_disagreement_emits_review_marker():
    span_id = str(uuid.uuid4())
    mock_span = ExtractedSpan(
        span_id=span_id,
        region_id="panel",
        polygon=[(0, 0), (10, 0), (10, 10), (0, 10)],
        text="150",
        confidence=0.99,
        source_provider=EvidenceProvider.PADDLEOCR,
    )
    result = arbitrate_mrp("150", "1S0", span_id=span_id, primary_reading=mock_span)
    assert result.needs_review is True
    assert result.primary_provider == EvidenceProvider.PADDLEOCR
    assert result.secondary_provider == EvidenceProvider.TESSERACT


@patch("pytesseract.image_to_string")
def test_synthetic_glyph_confusion_correction(mock_image_to_string, tmp_path):
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        pytest.skip("PIL required")
    img = Image.new("RGB", (250, 80), color="white")
    ImageDraw.Draw(img).text((15, 20), "1S0", fill="black")
    dummy_tess = tmp_path / "tessdata"
    dummy_tess.mkdir()

    def side_effect(image, config=""):
        return "10" if "tessedit_char_whitelist" in config else "1S0"

    mock_image_to_string.side_effect = side_effect
    text = extract_mrp_quantity(np.array(img), str(dummy_tess))
    assert "S" not in text


@patch("app.modules.vision.ocr.extract_mrp_quantity")
def test_arbitrate_field_declaration_wiring(mock_extract):
    mock_extract.return_value = "100"
    span_id = str(uuid.uuid4())
    primary_span = ExtractedSpan(
        span_id=span_id,
        region_id="panel",
        polygon=[(10, 10), (50, 10), (50, 50), (10, 50)],
        text="100",
        confidence=0.99,
        source_provider=EvidenceProvider.PADDLEOCR,
    )
    result = arbitrate_field_declaration(
        np.zeros((100, 100, 3), dtype=np.uint8), primary_span, "/fake/dir"
    )
    assert result.needs_review is False
    mock_extract.assert_called_once()
