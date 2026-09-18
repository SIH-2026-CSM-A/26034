"""An officer confirms a category; the capture is evaluated again under it, as a new scan.

Two claims, kept apart. The behavioural one: confirming moves the sector-gated findings
off ``UNCONFIRMED_CATEGORY_REASON``, and only an officer's stated category does that — a
live proposal sitting on the scan never does. The structural one: nothing in the
application assigns ``product_category`` on a scan row after construction, so the only
writer is still ``new_scan``, fed from a typed request body.
"""

import ast
from pathlib import Path
from unittest.mock import patch

import cv2
import pytest
from httpx import AsyncClient

from app.core import Scan, ScanStatus, get_session_factory
from app.pipeline.rule_findings import UNCONFIRMED_CATEGORY_REASON
from tests.pipeline.conftest import CONTROLLER, INSPECTOR, OTHER_INSPECTOR, auth
from tests.pipeline.test_api import LISTING
from tests.pipeline.test_image_submission import _detection
from tests.pipeline.test_orchestrator import PANEL_SPANS, a_span, scan_panel_frame

pytestmark = pytest.mark.postgres

APP = Path(__file__).resolve().parents[2] / "app"
FOOD_SPANS = [*PANEL_SPANS, a_span("FSSAI Lic. No. 10012031000123", "s-fssai", 330)]


def _gated(detail: dict) -> list[dict]:
    return [f for f in detail["findings"] if f["reason"] == UNCONFIRMED_CATEGORY_REASON]


async def _submit_image(client: AsyncClient) -> dict:
    ok, encoded = cv2.imencode(".jpg", scan_panel_frame())
    assert ok
    response = await client.post(
        "/scans/image",
        files={"image": ("capture.jpg", encoded.tobytes(), "image/jpeg")},
        data={"calibration_method": "none", "ward": "Ward 91 Khairatabad"},
        headers=auth(INSPECTOR),
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _read(client: AsyncClient, scan_id: str, principal=INSPECTOR) -> dict:
    response = await client.get(f"/scans/{scan_id}", headers=auth(principal))
    assert response.status_code == 200, response.text
    return response.json()


async def _confirm(client: AsyncClient, scan_id: str, body: dict, principal=INSPECTOR):
    return await client.post(f"/scans/{scan_id}/category", json=body, headers=auth(principal))


def _vision():
    return (
        patch("app.pipeline.orchestrator.detect_pdp", return_value=_detection()),
        patch("app.pipeline.orchestrator.extract_panel_text", return_value=FOOD_SPANS),
    )


async def test_confirming_a_category_re_evaluates_the_held_capture_as_a_new_scan(
    client: AsyncClient,
) -> None:
    detect, read = _vision()
    with detect, read:
        original = await _read(client, (await _submit_image(client))["id"])
        assert original["product_category"] is None
        assert _gated(original), "nothing was sector-gated, so confirming proves nothing"

        response = await _confirm(client, original["id"], {"product_category": "food"})
        assert response.status_code == 201, response.text
        confirmed = await _read(client, response.json()["id"])

    assert confirmed["id"] != original["id"]
    assert confirmed["status"] == ScanStatus.COMPLETE
    assert confirmed["product_category"] == "food"
    assert _gated(confirmed) == []
    # The original is a record of an evaluation made with no category, and stays one.
    untouched = await _read(client, original["id"])
    assert untouched["product_category"] is None
    assert untouched["findings"] == original["findings"]


async def test_a_live_proposal_never_becomes_the_confirmed_category(client: AsyncClient) -> None:
    """The pipeline proposes ``food``; the officer says ``cosmetics``; cosmetics is stored.

    And before any confirmation, with the proposal live on the scan, the confirmed field is
    null and every gated finding is still gated.
    """
    detect, read = _vision()
    with detect, read:
        original = await _read(client, (await _submit_image(client))["id"])
        assert original["category_proposal"] is not None
        assert original["category_proposal"]["category"] == "food"
        assert original["product_category"] is None
        assert _gated(original)

        for body in ({}, {"accept_proposal": True}, {"product_category": None}):
            refused = await _confirm(client, original["id"], body)
            assert refused.status_code == 422, (body, refused.text)

        response = await _confirm(client, original["id"], {"product_category": "cosmetics"})
        confirmed = await _read(client, response.json()["id"])

    assert confirmed["product_category"] == "cosmetics"
    assert confirmed["category_proposal"]["category"] == "food"


async def test_a_listing_is_re_evaluated_from_the_stored_record(client: AsyncClient) -> None:
    submitted = (await client.post("/scans", json=LISTING, headers=auth(INSPECTOR))).json()
    assert _gated(submitted)

    response = await _confirm(client, submitted["id"], {"product_category": "food"})

    assert response.status_code == 201, response.text
    assert response.json()["product_category"] == "food"
    assert _gated(response.json()) == []


async def test_the_re_evaluation_stays_in_the_original_scans_territory(
    client: AsyncClient,
) -> None:
    """A controller confirms; the district inspector who filed the scan still sees the result."""
    submitted = (await client.post("/scans", json=LISTING, headers=auth(INSPECTOR))).json()

    response = await _confirm(client, submitted["id"], {"product_category": "food"}, CONTROLLER)

    assert response.status_code == 201, response.text
    await _read(client, response.json()["id"], INSPECTOR)
    async with get_session_factory()() as session:
        row = await session.get(Scan, response.json()["id"])
    assert (row.state, row.region, row.district) == ("Maharashtra", "Pune", "Satara")
    assert row.officer_id == CONTROLLER.subject
    assert row.capture_metadata["re_evaluation_of"] == submitted["id"]


async def test_confirmation_is_an_authenticated_in_jurisdiction_officer_act(
    client: AsyncClient,
) -> None:
    submitted = (await client.post("/scans", json=LISTING, headers=auth(INSPECTOR))).json()
    url = f"/scans/{submitted['id']}/category"

    assert (await client.post(url, json={"product_category": "food"})).status_code == 401
    outsider = await _confirm(
        client, submitted["id"], {"product_category": "food"}, OTHER_INSPECTOR
    )
    assert outsider.status_code == 404


async def test_a_scan_whose_capture_is_not_held_is_a_409(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.core import get_settings

    monkeypatch.setenv("CAPTURE_STORE_DIR", "")
    get_settings.cache_clear()
    detect, read = _vision()
    with detect, read:
        submitted = await _submit_image(client)
        response = await _confirm(client, submitted["id"], {"product_category": "food"})

    assert response.status_code == 409, response.text


def test_nothing_assigns_a_scans_product_category_after_construction() -> None:
    """No ``<anything>.product_category = ...`` anywhere in the application.

    ``new_scan`` is the only writer (``test_category_proposal_is_not_a_confirmation``
    pins that construction site), so a confirmed category can only ever be the argument a
    route handed it. An attribute assignment is the one edit that would open a second way
    in — including for a proposal — and this is what refuses it.
    """
    files = sorted(APP.rglob("*.py"))
    assert len(files) > 20, f"only {len(files)} python files found under {APP}"
    offenders = []
    for path in files:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            targets = (
                node.targets
                if isinstance(node, ast.Assign)
                else [node.target]
                if isinstance(node, ast.AugAssign | ast.AnnAssign)
                else []
            )
            for target in targets:
                if isinstance(target, ast.Attribute) and target.attr == "product_category":
                    offenders.append(f"{path.relative_to(APP)}:{node.lineno}")
    assert offenders == []


def test_the_confirmation_route_reads_nothing_the_pipeline_proposed() -> None:
    """``confirm_category`` mentions no proposal, display category or capture outcome."""
    tree = ast.parse((APP / "pipeline" / "router.py").read_text(encoding="utf-8"))
    (route,) = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "confirm_category"
    ]
    names = {n.id for n in ast.walk(route) if isinstance(n, ast.Name)} | {
        n.attr for n in ast.walk(route) if isinstance(n, ast.Attribute)
    }
    assert "product_category" in names  # the walk sees the body, so an empty result means something
    forbidden = {
        "category_proposal",
        "display_category",
        "capture_outcome",
        "capture_outcome_json",
        "CaptureOutcome",
        "CategoryProposal",
        "propose_category",
    }
    assert names & forbidden == set()
