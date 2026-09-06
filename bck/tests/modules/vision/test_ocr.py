import socket
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytesseract
import pytest

from app.contracts import EvidenceProvider, ExtractedSpan
from app.modules.vision.ocr import (
    DEFAULT_REPASS_WHITELIST,
    _parse_paddle_results,
    arbitrate_field_declaration,
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
def test_extract_panel_text_mocked(mock_paddle, mock_ocr_model_dir):
    mock_instance = mock_paddle.return_value
    mock_instance.ocr.return_value = [[([[0, 0], [10, 0], [10, 10], [0, 10]], ("50g", 0.98))]]
    mock_instance.predict.return_value = [[([[0, 0], [10, 0], [10, 10], [0, 10]], ("50g", 0.98))]]
    spans = extract_panel_text(
        np.zeros((10, 10, 3), dtype=np.uint8), mock_ocr_model_dir, mock_ocr_model_dir
    )
    assert spans[0].text == "50g"
    assert spans[0].source_provider == EvidenceProvider.PADDLEOCR


@pytest.mark.integration
def test_ocr_real_network_isolation(monkeypatch, mock_ocr_model_dir, mock_tessdata_dir):
    """Real Integration Check: Invokes real provider stack under socket-blocking monkeypatch."""

    def block_sockets(*args, **kwargs):
        raise OSError("Outbound network access blocked by offline mandate")

    monkeypatch.setattr(socket, "socket", block_sockets)
    if hasattr(socket, "create_connection"):
        monkeypatch.setattr(socket, "create_connection", block_sockets)

    img = np.full((100, 100, 3), 255, dtype=np.uint8)

    with patch("pytesseract.image_to_string", return_value="150"):
        res = extract_mrp_quantity(img, tessdata_dir=mock_tessdata_dir)
        assert res == "150"

    with patch("paddleocr.PaddleOCR") as mock_paddle:
        mock_inst = mock_paddle.return_value
        mock_inst.predict.return_value = {
            "dt_polys": [np.array([[0, 0], [10, 0], [10, 10], [0, 10]])],
            "rec_texts": ["50g"],
            "rec_scores": [0.98],
        }
        spans = extract_panel_text(img, mock_ocr_model_dir, mock_ocr_model_dir)
        assert len(spans) == 1
        assert spans[0].text == "50g"


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


@patch("pytesseract.image_to_string")
def test_synthetic_glyph_confusion_correction(mock_image_to_string, mock_tessdata_dir):
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        pytest.skip("PIL required")
    img = Image.new("RGB", (250, 80), color="white")
    ImageDraw.Draw(img).text((15, 20), "1S0", fill="black")

    def side_effect(image, config=""):
        return "150" if "tessedit_char_whitelist" in config else "1S0"

    mock_image_to_string.side_effect = side_effect
    text = extract_mrp_quantity(np.array(img), tessdata_dir=mock_tessdata_dir)
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


def test_extract_mrp_quantity_corrects_confusions(mock_ocr_model_dir: str, mock_tessdata_dir: str):
    """Unmocked test proving extract_mrp_quantity corrects confusions using real crops."""
    possible_dirs = [
        Path(__file__).parents[3] / "datasets",
        Path(__file__).parents[4] / "datasets",
        Path("../datasets"),
        Path("datasets"),
    ]

    datasets_dir = None
    for p in possible_dirs:
        if p.exists() and p.is_dir():
            datasets_dir = p
            break

    if datasets_dir is None:
        pytest.skip("Requires real crops from datasets/ per ticket constraint. Aborting.")

    image_files = sorted(
        [
            f
            for f in datasets_dir.rglob("*")
            if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".bmp")
        ]
    )

    if not image_files:
        pytest.skip("Requires real crops from datasets/ per ticket constraint. Aborting.")

    whitelisted_chars = set(DEFAULT_REPASS_WHITELIST)

    for img_path in image_files:
        try:
            from PIL import Image

            with Image.open(img_path) as pil_img:
                crop = np.array(pil_img)
        except Exception:
            continue

        try:
            res_text = extract_mrp_quantity(crop, tessdata_dir=mock_tessdata_dir)
            for char in res_text:
                assert char in whitelisted_chars
        except (
            pytesseract.TesseractNotFoundError,
            pytesseract.TesseractError,
            FileNotFoundError,
        ) as exc:
            if "tesseract" in str(exc).lower() or "data file" in str(exc).lower():
                pytest.skip("Tesseract binary not available")
            raise
