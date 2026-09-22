"""The photograph's digest is chained at ingestion, before anything reads it.

Driven through the API against a real database, because the ordering under test is a
database ordering: the capture entry is staged in the transaction that inserts the scan,
and the verdict entry has to find it and append rather than start a second genesis. A pure
test of the chain functions cannot see either of those.
"""

import hashlib
from unittest.mock import patch

import cv2
import numpy as np
import pytest
from httpx import AsyncClient

from app.contracts import EvidenceAssetType
from app.modules.evidence import verify_chain
from app.modules.evidence.domain import EvidenceEntry
from app.modules.evidence.service import asset_digest, record_from
from tests.pipeline.conftest import INSPECTOR, auth
from tests.pipeline.test_orchestrator import PANEL_SPANS, scan_panel_frame

pytestmark = pytest.mark.asyncio


class _Detection:
    bbox = (60, 60, 680, 480)
    area = 326400
    confidence = 0.81
    method = "heuristic"


def _jpeg(frame: np.ndarray) -> bytes:
    ok, encoded = cv2.imencode(".jpg", frame)
    assert ok
    return encoded.tobytes()


async def _entries(client: AsyncClient, scan_id: str) -> list[dict]:
    response = await client.get(f"/scans/{scan_id}/evidence", headers=auth(INSPECTOR))
    assert response.status_code == 200, response.text
    return response.json()


async def _submit(client: AsyncClient, payload: bytes) -> str:
    """Submit and let evaluation finish, with the two models stood in for as elsewhere.

    The stand-ins are only so a verdict exists to append; nothing here asserts anything
    about what they returned. The digest under test is taken before either of them runs.
    """
    with (
        patch("app.pipeline.orchestrator.detect_pdp", return_value=_Detection()),
        patch("app.pipeline.orchestrator.extract_panel_text", return_value=PANEL_SPANS),
    ):
        response = await client.post(
            "/scans/image",
            files={"image": ("capture.jpg", payload, "image/jpeg")},
            data={"calibration_method": "none"},
            headers=auth(INSPECTOR),
        )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] != "failed", body
    return body["id"]


async def test_the_chain_opens_with_the_digest_of_the_bytes_received(
    client: AsyncClient,
) -> None:
    """Sequence 0 is the photograph, and its digest is ``sha256`` of what was uploaded."""
    payload = _jpeg(scan_panel_frame())
    scan_id = await _submit(client, payload)

    view = await _entries(client, scan_id)
    genesis = view["entries"][0]
    assert genesis["sequence"] == 0
    assert genesis["asset_type"] == EvidenceAssetType.PRODUCT_IMAGE

    # The digest itself is not in the summary view, so read it the way the report does.
    entries = await _chain(client, scan_id)
    digest, note = asset_digest(entries)
    assert note is None
    assert digest == hashlib.sha256(payload).hexdigest()


async def _chain(client: AsyncClient, scan_id: str) -> list[EvidenceEntry]:
    """Rebuild the chain from the rows the API exposes plus the stored payloads.

    The evidence view summarises entries and omits payloads, so this reaches for the rows
    the same way the report path does — through the session the app is using.
    """
    from sqlalchemy import select

    from app.core.db import get_session_factory
    from app.core.models import EvidenceEntryRow

    factory = get_session_factory()
    async with factory() as session:
        rows = (
            (
                await session.execute(
                    select(EvidenceEntryRow)
                    .where(EvidenceEntryRow.scan_id == scan_id)
                    .order_by(EvidenceEntryRow.sequence)
                )
            )
            .scalars()
            .all()
        )
    return [
        EvidenceEntry(
            sequence=row.sequence,
            timestamp=row.timestamp,
            payload_hash=row.payload_hash,
            prev_hash=row.prev_hash,
            entry_hash=row.entry_hash,
            payload=row.payload_json,
            asset_type=row.asset_type,
        )
        for row in rows
    ]


async def test_the_verdict_appends_to_the_capture_and_the_chain_verifies(
    client: AsyncClient,
) -> None:
    """Two entries, linked, and the verdict is still findable though it is no longer first."""
    payload = _jpeg(scan_panel_frame())
    scan_id = await _submit(client, payload)
    entries = await _chain(client, scan_id)

    assert [entry.sequence for entry in entries] == [0, 1]
    assert entries[0].asset_type == EvidenceAssetType.PRODUCT_IMAGE
    assert entries[1].asset_type == EvidenceAssetType.AUDIT_LOG
    assert entries[1].prev_hash == entries[0].entry_hash

    verification = verify_chain(entries)
    assert verification.is_valid, verification.reason

    record = record_from(entries)
    assert record.subject_ref == scan_id
    assert record.findings


async def test_the_digest_is_not_the_entry_s_payload_hash(client: AsyncClient) -> None:
    """The certificate must print a number a filed photograph can be matched to.

    The payload hash covers the whole capture record — digest, byte length, storage key,
    media type — and matches no file.
    """
    payload = _jpeg(scan_panel_frame())
    entries = await _chain(client, await _submit(client, payload))
    digest, _ = asset_digest(entries)
    assert digest == hashlib.sha256(payload).hexdigest()
    assert digest != entries[0].payload_hash


async def test_two_submissions_of_the_same_photograph_record_the_same_digest(
    client: AsyncClient,
) -> None:
    """Content-addressed: the digest is of the bytes, not of the submission."""
    payload = _jpeg(scan_panel_frame())
    first, _ = asset_digest(await _chain(client, await _submit(client, payload)))
    second, _ = asset_digest(await _chain(client, await _submit(client, payload)))
    assert first == second == hashlib.sha256(payload).hexdigest()


async def test_issuing_a_report_does_not_empty_the_scan_s_panel_spans(
    client: AsyncClient,
) -> None:
    """The spans are read from the entry that carries them, not from whatever is last.

    Issuing a report appends the export's digest to the chain. Reading the highest-sequence
    entry then found an export payload, which has no spans, and the consumer result page —
    whose ingredient list and barcode line are built from them — went blank for everyone.
    """
    payload = _jpeg(scan_panel_frame())
    scan_id = await _submit(client, payload)

    before = (await client.get(f"/scans/{scan_id}", headers=auth(INSPECTOR))).json()
    assert before["panel_spans"], "no spans to lose, so this test would prove nothing"

    review = await client.post(
        f"/scans/{scan_id}/review",
        json={"action": "confirm"},
        headers=auth(INSPECTOR),
    )
    assert review.status_code == 201, review.text
    issued = await client.post(
        f"/scans/{scan_id}/evidence/report", params={"format": "pdf"}, headers=auth(INSPECTOR)
    )
    assert issued.status_code == 201, issued.text
    entries = await _chain(client, scan_id)
    assert len(entries) == 3, "the export did not reach the chain, so nothing was at risk"

    after = (await client.get(f"/scans/{scan_id}", headers=auth(INSPECTOR))).json()
    assert after["panel_spans"] == before["panel_spans"]
