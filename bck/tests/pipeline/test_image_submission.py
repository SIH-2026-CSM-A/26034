"""The image route answers before evaluation and stores everything evaluation says.

A phone on a mobile network drops a request that sits silent for the length of an OCR
run, so ``POST /scans/image`` returns the scan at PROCESSING and evaluation finishes on a
background task. What that task reports has to reach the officer through
``GET /scans/{id}`` alone — the verdict and findings in their tables, and the capture
instruction, category proposal and display category on the row — because there is no
other response left to carry them.

Driven over ASGI, the background task runs before ``client.post`` returns, so the read
that follows sees the finished state. That is the transport's behaviour, not the
server's; the assertions are about what the read reports, which holds either way.
"""

from unittest.mock import patch

import cv2
import numpy as np
import pytest
from httpx import AsyncClient

from app.core import CalibrationMethod, ScanStatus
from app.modules.vision.preprocess import QualityReason
from app.pipeline import router
from app.pipeline.orchestrator import Calibration, run_image_scan
from app.pipeline.schemas import CaptureOutcome
from tests.pipeline.conftest import INSPECTOR, auth
from tests.pipeline.test_orchestrator import (
    NOW,
    PANEL_SPANS,
    a_span,
    blurred_image,
    scan_panel_frame,
)

pytestmark = pytest.mark.asyncio


def _jpeg(frame: np.ndarray) -> bytes:
    ok, encoded = cv2.imencode(".jpg", frame)
    assert ok
    return encoded.tobytes()


async def _submit(client: AsyncClient, frame: np.ndarray) -> dict:
    response = await client.post(
        "/scans/image",
        files={"image": ("capture.jpg", _jpeg(frame), "image/jpeg")},
        data={"calibration_method": "none"},
        headers=auth(INSPECTOR),
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _read(client: AsyncClient, scan_id: str) -> dict:
    response = await client.get(f"/scans/{scan_id}", headers=auth(INSPECTOR))
    assert response.status_code == 200, response.text
    return response.json()


async def test_the_submission_response_carries_no_verdict(client: AsyncClient) -> None:
    """The response is the row to poll against, and says nothing about the package."""
    submitted = await _submit(client, blurred_image())
    assert submitted["status"] == ScanStatus.PROCESSING
    assert submitted["verdict"] is None
    assert submitted["findings"] == []
    assert submitted["quality"] is None
    assert submitted["category_proposal"] is None


async def test_a_refused_capture_is_read_back_with_its_instruction(client: AsyncClient) -> None:
    """The officer polling for the outcome is told to capture again, not left at a status."""
    submitted = await _submit(client, blurred_image())
    detail = await _read(client, submitted["id"])
    assert detail["status"] == ScanStatus.RECEIVED
    assert detail["verdict"] is None
    assert detail["quality"]["reason_code"] == QualityReason.BLUR_EXCEEDED
    assert "capture again" in detail["quality"]["instruction"]


async def test_an_evaluated_capture_is_read_back_whole(client: AsyncClient) -> None:
    """Verdict, findings, proposal and display category all survive the round trip.

    The expected values come from running the pipeline directly on the same frame with
    the same stand-ins for detection and OCR, so the assertion is equality with what
    evaluation produced, not with a value written into this test.
    """
    frame = scan_panel_frame()
    # An FSSAI licence line, so the extraction module proposes a category and the
    # assertion below is on a stored value rather than on two ``None``s agreeing.
    spans = [*PANEL_SPANS, a_span("FSSAI Lic. No. 10012031000123", "s-fssai", 330)]
    with (
        patch("app.pipeline.orchestrator.detect_pdp", return_value=_detection()),
        patch("app.pipeline.orchestrator.extract_panel_text", return_value=spans),
    ):
        expected = run_image_scan(
            frame,
            calibration=Calibration(method=CalibrationMethod.NONE),
            product_category=None,
            evaluated_at=NOW,
            subject_ref="expected",
        )
        submitted = await _submit(client, frame)

    detail = await _read(client, submitted["id"])
    assert expected.category_proposal is not None  # or the round trip below proves nothing
    assert detail["status"] == ScanStatus.COMPLETE
    assert detail["verdict"] == expected.verdict.verdict
    assert {(f["field"], f["state"]) for f in detail["findings"]} == {
        (f.field, f.state) for f in expected.verdict.findings
    }
    # Serialised through the same schema the route uses, so the comparison is JSON to JSON.
    stored = CaptureOutcome(
        category_proposal=expected.category_proposal, display_category=expected.display_category
    ).model_dump(mode="json")
    assert detail["category_proposal"] == stored["category_proposal"]
    assert detail["display_category"] == stored["display_category"]


async def test_a_crash_during_evaluation_is_read_back_as_failed(client: AsyncClient) -> None:
    """Nothing leaves a scan at PROCESSING: a stage that raises marks it FAILED."""
    with patch.object(router, "run_image_scan", side_effect=RuntimeError("stage crashed")):
        submitted = await _submit(client, blurred_image())
    detail = await _read(client, submitted["id"])
    assert detail["status"] == ScanStatus.FAILED
    assert detail["verdict"] is None


def _detection():
    class _Detection:
        bbox = (60, 60, 680, 480)
        area = 326400
        confidence = 0.81

    return _Detection()
