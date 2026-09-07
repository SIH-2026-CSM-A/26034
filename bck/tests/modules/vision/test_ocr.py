import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.contracts import EvidenceProvider, ExtractedSpan
from app.modules.vision.ocr import (
    _parse_paddle_results,
    arbitrate_mrp,
    extract_mrp_quantity,
    extract_panel_text,
)


@pytest.fixture
def mock_ocr_model_dir(tmp_path: Path) -> str:
    """Fixture providing a valid local directory path for PaddleOCR models."""
    model_dir = tmp_path / "paddleocr_model"
    model_dir.mkdir()
    return str(model_dir)


@pytest.fixture
def mock_tessdata_dir(tmp_path: Path) -> str:
    """Fixture providing a valid local tessdata directory path."""
    tessdata = tmp_path / "tessdata"
    tessdata.mkdir()
    system_eng = None
    for cand in [
        Path("/usr/share/tesseract-ocr/5/tessdata/eng.traineddata"),
        Path("/usr/share/tesseract-ocr/4.00/tessdata/eng.traineddata"),
        Path("/usr/share/tessdata/eng.traineddata"),
    ]:
        if cand.exists():
            system_eng = cand
            break
    if system_eng:
        (tessdata / "eng.traineddata").write_bytes(system_eng.read_bytes())
    else:
        (tessdata / "eng.traineddata").write_bytes(b"mock_tessdata")
    return str(tessdata)


@patch("pytesseract.image_to_string")
def test_extract_mrp_quantity_mocked(mock_tesseract, mock_tessdata_dir):
    mock_tesseract.return_value = "Rs 150"
    img = np.full((100, 300, 3), 255, dtype=np.uint8)
    result = extract_mrp_quantity(img, tessdata_dir=mock_tessdata_dir)
    assert "150" in result
    assert "Rs" in result


@patch("paddleocr.PaddleOCR")
def test_extract_panel_text_mocked(mock_paddle, tmp_path):
    mock_instance = mock_paddle.return_value
    mock_instance.predict.return_value = {
        "dt_polys": [[[0, 0], [10, 0], [10, 10], [0, 10]]],
        "rec_texts": ["TEST"],
        "rec_scores": [0.99],
    }

    det_dir = str(tmp_path / "det")
    rec_dir = str(tmp_path / "rec")
    import os

    os.makedirs(det_dir)
    os.makedirs(rec_dir)

    import numpy as np

    image = np.zeros((100, 100, 3), dtype=np.uint8)
    spans = extract_panel_text(image, det_dir, rec_dir)

    assert len(spans) == 1
    assert spans[0].text == "TEST"
    assert spans[0].confidence == 0.99

    mock_paddle.assert_called_once()
    kwargs = mock_paddle.call_args.kwargs
    assert kwargs.get("text_detection_model_dir") == det_dir
    assert kwargs.get("text_recognition_model_dir") == rec_dir


def test_offline_guarantee_raises_on_missing_tessdata():
    with pytest.raises(FileNotFoundError):
        extract_mrp_quantity(np.zeros((10, 10, 3), dtype=np.uint8), "/invalid/path")


def test_offline_guarantee_missing_tessdata_dir(mock_ocr_model_dir: str, tmp_path: Path):
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    invalid_tessdata = str(tmp_path / "missing_tessdata")
    with pytest.raises(FileNotFoundError):
        extract_mrp_quantity(img, tessdata_dir=invalid_tessdata)


def test_arbitration_currency_normalization():
    """Proves that ₹150 and Rs. 150 agree on value without flagging a review."""
    span_id = str(uuid.uuid4())
    mock_span = ExtractedSpan(
        span_id=span_id,
        region_id="panel",
        polygon=[(0, 0), (10, 0), (10, 10), (0, 10)],
        text="₹150",
        confidence=0.99,
        source_provider=EvidenceProvider.PADDLEOCR,
    )
    result = arbitrate_mrp("₹150", "Rs. 150", span_id=span_id, primary_reading=mock_span)
    assert result.needs_review is False
    assert result.agreed_text == "₹150"


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


def test_paddleocr_3x_parser_format():
    """PaddleOCR 3.x Parser Fix: Test parsing dt_polys, rec_texts, rec_scores dict/object."""
    paddle_3x_dict = {
        "dt_polys": [np.array([[10, 10], [100, 10], [100, 50], [10, 50]])],
        "rec_texts": ["Net Qty 500g"],
        "rec_scores": [0.98],
    }

    spans = _parse_paddle_results(paddle_3x_dict)
    assert len(spans) == 1
    assert spans[0].text == "Net Qty 500g"
    assert spans[0].confidence == 0.98
    assert spans[0].source_provider == EvidenceProvider.PADDLEOCR
    assert len(spans[0].polygon) == 4

    paddle_3x_obj = MagicMock()
    paddle_3x_obj.dt_polys = [np.array([[5, 5], [50, 5], [50, 25], [5, 25]])]
    paddle_3x_obj.rec_texts = ["MRP Rs 99"]
    paddle_3x_obj.rec_scores = [0.99]

    spans_obj = _parse_paddle_results(paddle_3x_obj)
    assert len(spans_obj) == 1
    assert spans_obj[0].text == "MRP Rs 99"
    assert spans_obj[0].confidence == 0.99
    assert len(spans_obj[0].polygon) == 4
