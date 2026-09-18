"""``POST /scans/artwork`` and the three package confirmations, through the real app.

The artwork route is the one HTTP path on which a millimetre is exact, so the assertion
that matters is the one on the figure: read back through the API it carries no interval.
The confirmations are asserted at the boundary the pipeline reads them from — the
keyword the orchestrator receives — and once more after a category confirmation, because
a re-evaluation that dropped them would silently re-apply Rule 7 to a package an officer
had said it does not govern.
"""

from unittest.mock import patch

import cv2
import pytest
from httpx import AsyncClient

from app.core import ScanStatus
from app.modules.measurement import PackageShape
from app.modules.vision.preprocess import QualityReason
from app.pipeline import router
from app.pipeline.orchestrator import PackageConfirmations, QualityRejection
from tests.pipeline.conftest import INSPECTOR, auth
from tests.pipeline.test_artwork_scan import LABEL, artwork, spans_from
from tests.pipeline.test_orchestrator import scan_panel_frame

pytestmark = pytest.mark.postgres

CONFIRMED = {
    "package_shape": "cylindrical",
    "declarations_required_under_other_law": "true",
    "rule_33_relaxation_granted": "true",
}
EXPECTED = PackageConfirmations(
    shape=PackageShape.CYLINDRICAL,
    declarations_required_under_other_law=True,
    rule_33_relaxation_granted=True,
)


async def _read(client: AsyncClient, scan_id: str) -> dict:
    response = await client.get(f"/scans/{scan_id}", headers=auth(INSPECTOR))
    assert response.status_code == 200, response.text
    return response.json()


async def _submit_artwork(client: AsyncClient, payload: bytes, name: str, data: dict | None = None):
    return await client.post(
        "/scans/artwork",
        files={"artwork": (name, payload, "application/octet-stream")},
        data={"product_category": "food", **(data or {})},
        headers=auth(INSPECTOR),
    )


async def test_artwork_is_measured_exactly_through_the_route(client: AsyncClient) -> None:
    pdf = artwork(LABEL)
    with patch("app.pipeline.orchestrator.extract_panel_text", return_value=spans_from(pdf)):
        response = await _submit_artwork(client, pdf, "label.pdf")
    assert response.status_code == 201, response.text
    assert response.json()["status"] == ScanStatus.PROCESSING

    detail = await _read(client, response.json()["id"])
    assert detail["status"] == ScanStatus.COMPLETE
    assert detail["refusal"] is None
    table = next(
        f
        for f in detail["findings"]
        if f["rule_snapshot"]["rule_id"] == "R7-2-TABLE-I" and f["field"] == "NET_QUANTITY"
    )
    assert table["state"] == "PASS"
    assert table["expected_value"] == "1.5 mm"
    assert float(table["observed_value"].split()[0]) == pytest.approx(3.47, abs=0.05)
    assert "±" not in table["observed_value"], "artwork is exact; there is no interval"


async def test_an_unsupported_artwork_type_is_refused_at_the_request(client: AsyncClient) -> None:
    response = await _submit_artwork(client, b"\x89PNG", "label.png")
    assert response.status_code == 422
    assert "pdf, svg" in response.json()["detail"]


async def test_unparseable_artwork_is_read_back_with_the_parsers_reason(
    client: AsyncClient,
) -> None:
    """Not a crash and not a quality rejection: the file was accepted and could not be read."""
    response = await _submit_artwork(client, b"this is not a pdf", "label.pdf")
    assert response.status_code == 201, response.text
    detail = await _read(client, response.json()["id"])
    assert detail["status"] == ScanStatus.RECEIVED
    assert detail["verdict"] is None
    assert detail["findings"] == []
    assert detail["quality"] is None
    assert detail["refusal"], "the officer must be told why, not left at a status"


def _rejection() -> QualityRejection:
    return QualityRejection(
        reason_code=QualityReason.BLUR_EXCEEDED,
        instruction="capture again",
        blur_score=0.0,
        glare_ratio=0.0,
        coverage_ratio=1.0,
    )


async def test_the_confirmations_reach_the_pipeline_and_survive_re_evaluation(
    client: AsyncClient,
) -> None:
    ok, encoded = cv2.imencode(".jpg", scan_panel_frame())
    assert ok
    with patch.object(router, "run_image_scan", return_value=_rejection()) as pipeline:
        submitted = await client.post(
            "/scans/image",
            files={"image": ("capture.jpg", encoded.tobytes(), "image/jpeg")},
            data={"calibration_method": "none", **CONFIRMED},
            headers=auth(INSPECTOR),
        )
        assert submitted.status_code == 201, submitted.text
        assert pipeline.call_args.kwargs["confirmations"] == EXPECTED

        confirmed = await client.post(
            f"/scans/{submitted.json()['id']}/category",
            json={"product_category": "food"},
            headers=auth(INSPECTOR),
        )
        assert confirmed.status_code == 201, confirmed.text
        assert pipeline.call_count == 2
        assert pipeline.call_args.kwargs["confirmations"] == EXPECTED


async def test_a_scan_submitted_with_no_confirmations_confirms_nothing(
    client: AsyncClient,
) -> None:
    ok, encoded = cv2.imencode(".jpg", scan_panel_frame())
    assert ok
    with patch.object(router, "run_image_scan", return_value=_rejection()) as pipeline:
        submitted = await client.post(
            "/scans/image",
            files={"image": ("capture.jpg", encoded.tobytes(), "image/jpeg")},
            data={"calibration_method": "none"},
            headers=auth(INSPECTOR),
        )
    assert submitted.status_code == 201, submitted.text
    assert pipeline.call_args.kwargs["confirmations"] == PackageConfirmations()


async def test_artwork_confirmations_survive_re_evaluation(client: AsyncClient) -> None:
    pdf = artwork(LABEL)
    with patch.object(router, "run_artwork_scan", return_value=_rejection()) as pipeline:
        submitted = await _submit_artwork(client, pdf, "label.pdf", CONFIRMED)
        assert submitted.status_code == 201, submitted.text
        assert pipeline.call_args.args[1] == "pdf"
        assert pipeline.call_args.kwargs["confirmations"] == EXPECTED
        confirmed = await client.post(
            f"/scans/{submitted.json()['id']}/category",
            json={"product_category": "food"},
            headers=auth(INSPECTOR),
        )
        assert confirmed.status_code == 201, confirmed.text
        assert pipeline.call_count == 2
        assert pipeline.call_args.args[0] == pdf, "the held artwork, not a decoded image"
        assert pipeline.call_args.kwargs["confirmations"] == EXPECTED
