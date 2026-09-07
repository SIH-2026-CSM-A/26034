from pathlib import Path
from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pytest

from app.modules.vision.pdp import (
    HEURISTIC_CONFIDENCE_PRIOR,
    HeuristicTextRegion,
    PDPResult,
    detect_pdp,
)


@pytest.fixture
def mock_pdp_model_file(tmp_path: Path) -> str:
    """Fixture providing a valid local file path for PDP weights."""
    weights_path = tmp_path / "pdp_detector.pt"
    weights_path.write_bytes(b"mock_binary_pdp_weights")
    return str(weights_path)


def printed_panel() -> np.ndarray:
    """A light frame with a block of print confined to its upper-left quadrant.

    Rows of small dark bars stand in for lines of text: close enough together that a
    closing kernel merges them, and nowhere near the right or bottom edges, so a bbox that
    reaches those edges is the frame rather than the print.
    """
    frame = np.full((300, 300, 3), 220, dtype=np.uint8)
    for row in range(100, 160, 12):
        for column in range(20, 130, 20):
            cv2.rectangle(frame, (column, row), (column + 12, row + 7), (20, 20, 20), -1)
    return frame


def test_detect_pdp_unset_weights_falls_back_to_heuristic(monkeypatch: pytest.MonkeyPatch):
    """No configured weights means the heuristic runs, not a refusal.

    This test previously asserted ``RuntimeError`` for all three of these inputs. VIS-008
    replaced that refusal deliberately: there is no PDP-trained model, so raising here left
    the application unable to serve a single scan. All three forms of "no weights" — unset
    environment, blank string, and a path that is not on disk — now route to the
    morphological fallback, which returns a type of its own.
    """
    monkeypatch.delenv("PDP_WEIGHTS_PATH", raising=False)
    image = printed_panel()

    assert isinstance(detect_pdp(image), HeuristicTextRegion)
    assert isinstance(detect_pdp(image, weights_path=""), HeuristicTextRegion)
    assert isinstance(
        detect_pdp(image, weights_path="non_existent_weights_file.pt"), HeuristicTextRegion
    )


def test_detect_pdp_empty_image(mock_pdp_model_file: str):
    empty_img = np.array([])

    with pytest.raises(ValueError):
        detect_pdp(empty_img, weights_path=mock_pdp_model_file)


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
    assert res.bbox == (20, 30, 100, 120)
    assert res.area == 12000
    assert res.confidence == 0.95


@patch("ultralytics.YOLO")
def test_detect_pdp_no_detection_refuses(mock_yolo_cls: MagicMock, mock_pdp_model_file: str):
    img = np.zeros((80, 120, 3), dtype=np.uint8)

    mock_boxes = MagicMock()
    mock_boxes.__len__.return_value = 0

    mock_results = [MagicMock()]
    mock_results[0].boxes = mock_boxes

    mock_model_instance = MagicMock()
    mock_model_instance.return_value = mock_results
    mock_yolo_cls.return_value = mock_model_instance

    with pytest.raises(ValueError):
        detect_pdp(img, weights_path=mock_pdp_model_file)


@patch("ultralytics.YOLO")
def test_detect_pdp_empty_detection_does_not_fall_back(
    mock_yolo_cls: MagicMock, mock_pdp_model_file: str
):
    """A detector that ran and found nothing is not the same as having no detector.

    The heuristic exists because there is no trained model. Where one is configured and
    reports no panel, that is evidence, and substituting a morphological guess for it would
    overwrite the finding with a number nobody chose. The frame here is one the heuristic
    would happily return a region for, so a fallback that fired would be visible.
    """
    mock_boxes = MagicMock()
    mock_boxes.__len__.return_value = 0

    mock_results = [MagicMock()]
    mock_results[0].boxes = mock_boxes

    mock_model_instance = MagicMock()
    mock_model_instance.return_value = mock_results
    mock_yolo_cls.return_value = mock_model_instance

    with pytest.raises(ValueError):
        detect_pdp(printed_panel(), weights_path=mock_pdp_model_file)


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


def test_heuristic_region_is_not_a_model_detection(monkeypatch: pytest.MonkeyPatch):
    """The fallback's result cannot be mistaken for a detection at the type level.

    Not a flag on a shared shape — a separate type that is not a ``PDPResult`` and is not a
    subclass of one, so an ``isinstance`` check written against the model type cannot pass
    vacuously over a guess. It carries no ``text``, because the heuristic reads glyph edges
    and never glyphs.
    """
    monkeypatch.delenv("PDP_WEIGHTS_PATH", raising=False)

    region = detect_pdp(printed_panel())

    assert isinstance(region, HeuristicTextRegion)
    assert not isinstance(region, PDPResult)
    assert not issubclass(HeuristicTextRegion, PDPResult)
    assert region.method == "heuristic"
    assert not hasattr(region, "text")


@patch("ultralytics.YOLO")
def test_model_detection_is_not_a_heuristic_region(
    mock_yolo_cls: MagicMock, mock_pdp_model_file: str
):
    """And the other direction, so the two cannot be collapsed from either side."""
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

    detection = detect_pdp(np.zeros((200, 200, 3), dtype=np.uint8), mock_pdp_model_file)

    assert isinstance(detection, PDPResult)
    assert not isinstance(detection, HeuristicTextRegion)
    assert not issubclass(PDPResult, HeuristicTextRegion)
    assert detection.method == "model"


def test_heuristic_finds_the_text_block_not_the_frame(monkeypatch: pytest.MonkeyPatch):
    """The region is the print, not the input handed back with a different name.

    The print occupies the upper-left of a 300x300 frame: the last bar ends at x=132 and
    the last row at y=155, and the morphological gradient widens each by a pixel on either
    side. A bbox inside those bounds plus a small tolerance is the block; a bbox reaching
    the far edges is the frame, which is the behaviour #63 removed.
    """
    monkeypatch.delenv("PDP_WEIGHTS_PATH", raising=False)

    region = detect_pdp(printed_panel())
    x, y, width, height = region.bbox

    assert x + width <= 136
    assert y + height <= 160
    assert region.area == float(width * height)
    assert region.area < 0.5 * 300 * 300


def test_heuristic_refuses_a_frame_spanning_region(monkeypatch: pytest.MonkeyPatch):
    """Edge texture everywhere yields one region covering the frame, and that is a refusal.

    Uniform noise has a gradient at every pixel, so the closing merges into a single
    contour spanning the image. Returning it would restate the frame as the panel and hand
    Rule 7 the largest area it could possibly band against.
    """
    monkeypatch.delenv("PDP_WEIGHTS_PATH", raising=False)
    noise = np.random.default_rng(0).integers(0, 255, (200, 200, 3), dtype=np.uint8)

    with pytest.raises(ValueError, match="No PDP detected in image."):
        detect_pdp(noise)


def test_heuristic_refuses_a_blank_frame(monkeypatch: pytest.MonkeyPatch):
    """A frame with no edges has no text region, and that is a refusal, not a full frame."""
    monkeypatch.delenv("PDP_WEIGHTS_PATH", raising=False)

    with pytest.raises(ValueError, match="No PDP detected in image."):
        detect_pdp(np.full((100, 100, 3), 128, dtype=np.uint8))


def test_heuristic_confidence_is_a_fixed_uncalibrated_prior(monkeypatch: pytest.MonkeyPatch):
    """Every heuristic region reports the same confidence, because nothing measures one.

    Pinned to the literal rather than read back off the constant, so a change to the value
    is a change a test notices. It is not 0.0: that was the value the removed full-image
    fallback reported, and reusing it would make a region indistinguishable from that
    defect's output.
    """
    monkeypatch.delenv("PDP_WEIGHTS_PATH", raising=False)

    wide = printed_panel()
    narrow = printed_panel()
    cv2.rectangle(narrow, (150, 200), (280, 280), (20, 20, 20), -1)

    first = detect_pdp(wide)
    second = detect_pdp(narrow)

    assert first.bbox != second.bbox
    assert first.confidence == second.confidence
    assert first.confidence == 0.3
    assert HEURISTIC_CONFIDENCE_PRIOR == 0.3
    assert first.confidence != 0.0


def test_heuristic_reads_an_image_from_a_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """The fallback accepts a path, not only an array — the same inputs the detector takes."""
    monkeypatch.delenv("PDP_WEIGHTS_PATH", raising=False)
    image_path = tmp_path / "panel.png"
    cv2.imwrite(str(image_path), printed_panel())

    region = detect_pdp(str(image_path))

    assert isinstance(region, HeuristicTextRegion)
    assert region.area > 0


def test_heuristic_refuses_an_unreadable_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """A path that is not an image refuses rather than crashing inside OpenCV."""
    monkeypatch.delenv("PDP_WEIGHTS_PATH", raising=False)
    not_an_image = tmp_path / "notes.txt"
    not_an_image.write_text("this is not a package photograph")

    with pytest.raises(ValueError, match="No PDP detected in image."):
        detect_pdp(str(not_an_image))
