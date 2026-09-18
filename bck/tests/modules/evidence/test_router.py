"""The evidence surface over real HTTP: a chain verified on read, a report past a human gate.

Postgres-marked like the scan routes, and built on their fixtures: a real app, real tokens,
a real database. The evidence router is mounted here on the application these tests build,
because ``app.main`` is not this module's to edit; what it proves is that the router works
the moment it is included.
"""

import json
from collections.abc import AsyncIterator
from unittest.mock import patch

import cv2
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, update

from app.core.db import get_session
from app.core.enums import ReviewAction
from app.core.models import EvidenceEntryRow
from tests.pipeline.conftest import INSPECTOR, OTHER_INSPECTOR, auth
from tests.pipeline.test_image_submission import _detection
from tests.pipeline.test_orchestrator import PANEL_SPANS, scan_panel_frame

pytestmark = pytest.mark.postgres


@pytest_asyncio.fixture
async def client(schema: None) -> AsyncIterator[AsyncClient]:
    """The real application with the evidence router mounted."""
    from app.main import create_app

    application = create_app()
    application.dependency_overrides[get_session] = get_session
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://pccs.test"
    ) as http:
        yield http


async def evaluated_scan(client: AsyncClient) -> str:
    ok, encoded = cv2.imencode(".jpg", scan_panel_frame())
    assert ok
    with (
        patch("app.pipeline.orchestrator.detect_pdp", return_value=_detection()),
        patch("app.pipeline.orchestrator.extract_panel_text", return_value=list(PANEL_SPANS)),
    ):
        response = await client.post(
            "/scans/image",
            files={"image": ("capture.jpg", encoded.tobytes(), "image/jpeg")},
            data={"calibration_method": "none", "ward": "Ward 91 Khairatabad"},
            headers=auth(INSPECTOR),
        )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def confirmed(client: AsyncClient, scan_id: str) -> None:
    review = await client.post(
        f"/scans/{scan_id}/review",
        json={"action": ReviewAction.CONFIRM.value},
        headers=auth(INSPECTOR),
    )
    assert review.status_code == 201, review.text


async def test_the_chain_is_verified_on_every_read(client: AsyncClient) -> None:
    scan_id = await evaluated_scan(client)
    view = (await client.get(f"/scans/{scan_id}/evidence", headers=auth(INSPECTOR))).json()
    assert view["verification"] == {
        "is_valid": True,
        "broken_link_index": None,
        "purged_indices": [],
        "reason": None,
    }
    assert [entry["sequence"] for entry in view["entries"]] == [0]


async def test_an_edited_entry_is_reported_broken_and_certifies_nothing(
    client: AsyncClient, configured: str
) -> None:
    """Change one byte of a stored payload; the read says so and no report can be issued."""
    from app.core.db import get_engine

    scan_id = await evaluated_scan(client)
    await confirmed(client, scan_id)
    async with get_engine().begin() as connection:
        row = (
            await connection.execute(
                select(EvidenceEntryRow.id, EvidenceEntryRow.payload_json).where(
                    EvidenceEntryRow.scan_id == scan_id
                )
            )
        ).one()
        edited = row.payload_json.replace('"verdict":"REVIEW"', '"verdict":"PASS"', 1)
        assert edited != row.payload_json, "the payload had no verdict to edit"
        await connection.execute(
            update(EvidenceEntryRow)
            .where(EvidenceEntryRow.id == row.id)
            .values(payload_json=edited)
        )

    view = (await client.get(f"/scans/{scan_id}/evidence", headers=auth(INSPECTOR))).json()
    assert view["verification"]["is_valid"] is False
    assert view["verification"]["reason"] == "payload_hash_mismatch"
    assert view["verification"]["broken_link_index"] == 0

    refused = await client.post(f"/scans/{scan_id}/evidence/report", headers=auth(INSPECTOR))
    assert refused.status_code == 409
    assert "does not verify" in refused.json()["detail"]


async def test_no_report_before_an_officer_finalises_the_review(client: AsyncClient) -> None:
    scan_id = await evaluated_scan(client)
    for fmt in ("json", "pdf", "docx"):
        refused = await client.post(
            f"/scans/{scan_id}/evidence/report", params={"format": fmt}, headers=auth(INSPECTOR)
        )
        assert refused.status_code == 409, fmt
        assert "not been" in refused.json()["detail"] or "finalized" in refused.json()["detail"]
    view = (await client.get(f"/scans/{scan_id}/evidence", headers=auth(INSPECTOR))).json()
    assert len(view["entries"]) == 1, "a refused export appends nothing"


async def test_a_confirmed_scan_yields_the_part_a_certificate_and_the_chain_records_it(
    client: AsyncClient,
) -> None:
    scan_id = await evaluated_scan(client)
    await confirmed(client, scan_id)

    issued = await client.post(f"/scans/{scan_id}/evidence/report", headers=auth(INSPECTOR))
    assert issued.status_code == 201, issued.text
    certificate = issued.json()
    assert certificate["statute_citation"] == "BSA §63(4) Part A"
    assert certificate["confirmation"]["officer_action"] == "CONFIRM"
    assert certificate["confirmation"]["confirmed_by"] == INSPECTOR.subject
    assert certificate["audit_trail"]["total_sequence_count"] == 1
    assert certificate["declarations"], "the certificate lists what was found"
    assert "paddleocr" in certificate["model_versions"]["ocr_engine"]
    assert "heuristic" in certificate["model_versions"]["pdp_detector"]

    view = (await client.get(f"/scans/{scan_id}/evidence", headers=auth(INSPECTOR))).json()
    assert view["verification"]["is_valid"] is True
    assert [entry["sequence"] for entry in view["entries"]] == [0, 1]
    assert view["entries"][1]["asset_type"] == "AUDIT_LOG"


async def test_the_filed_report_renders_and_its_digest_enters_the_chain(
    client: AsyncClient, configured: str
) -> None:
    import hashlib

    scan_id = await evaluated_scan(client)
    await confirmed(client, scan_id)
    pdf = await client.post(
        f"/scans/{scan_id}/evidence/report", params={"format": "pdf"}, headers=auth(INSPECTOR)
    )
    assert pdf.status_code == 201
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF")
    docx = await client.post(
        f"/scans/{scan_id}/evidence/report", params={"format": "docx"}, headers=auth(INSPECTOR)
    )
    assert docx.status_code == 201
    assert docx.content.startswith(b"PK")

    from app.core.db import get_engine

    async with get_engine().begin() as connection:
        payloads = (
            (
                await connection.execute(
                    select(EvidenceEntryRow.payload_json)
                    .where(EvidenceEntryRow.scan_id == scan_id)
                    .order_by(EvidenceEntryRow.sequence)
                )
            )
            .scalars()
            .all()
        )
    exports = [json.loads(p) for p in payloads[1:]]
    assert [e["format"] for e in exports] == ["pdf", "docx"]
    assert exports[0]["report_sha256"] == hashlib.sha256(pdf.content).hexdigest()
    assert exports[0]["exported_by"] == INSPECTOR.subject


async def test_another_jurisdiction_sees_no_chain_at_all(client: AsyncClient) -> None:
    scan_id = await evaluated_scan(client)
    hidden = await client.get(f"/scans/{scan_id}/evidence", headers=auth(OTHER_INSPECTOR))
    assert hidden.status_code == 404
    hidden = await client.post(f"/scans/{scan_id}/evidence/report", headers=auth(OTHER_INSPECTOR))
    assert hidden.status_code == 404


def test_the_production_app_serves_the_evidence_surface() -> None:
    """The mount in ``app.main``, read off the schema the app publishes.

    Read from ``openapi()`` and not from ``app.routes``: FastAPI wraps an included router
    in an ``_IncludedRouter`` with no ``path``, so the earlier spelling of this test raised
    before it could look, and was xfailing on that rather than on the missing mount.
    """
    from app.main import create_app

    paths = create_app().openapi()["paths"]
    assert "/scans/{scan_id}/evidence" in paths
    assert "/scans/{scan_id}/evidence/report" in paths
