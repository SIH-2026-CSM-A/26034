"""The unauthenticated consumer upload is limited before anything is stored or queued."""

import cv2
import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from app.core import Scan, get_session_factory
from app.pipeline import router
from tests.pipeline.test_orchestrator import blurred_image

pytestmark = [pytest.mark.asyncio, pytest.mark.postgres]


def _files() -> dict:
    ok, encoded = cv2.imencode(".jpg", blurred_image())
    assert ok
    return {"image": ("capture.jpg", encoded.tobytes(), "image/jpeg")}


async def _scan_count() -> int:
    async with get_session_factory()() as session:
        return (await session.scalar(select(func.count()).select_from(Scan))) or 0


async def test_a_client_past_its_limit_gets_a_429_and_no_scan_is_stored(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CONSUMER_SCANS_PER_CLIENT_PER_MINUTE", "2")
    from app.core import get_settings

    get_settings.cache_clear()
    headers = {"X-Real-IP": "198.51.100.4"}
    for _ in range(2):
        accepted = await client.post("/consumer/scans/image", files=_files(), headers=headers)
        assert accepted.status_code == 201, accepted.text

    refused = await client.post("/consumer/scans/image", files=_files(), headers=headers)

    assert refused.status_code == 429, refused.text
    assert int(refused.headers["Retry-After"]) >= 1
    assert await _scan_count() == 2

    other = await client.post(
        "/consumer/scans/image", files=_files(), headers={"X-Real-IP": "198.51.100.5"}
    )
    assert other.status_code == 201, other.text


async def test_a_full_queue_refuses_the_upload_and_a_finished_scan_frees_its_place(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(router, "_consumer_pending", 5)
    refused = await client.post("/consumer/scans/image", files=_files())
    assert refused.status_code == 429, refused.text
    assert await _scan_count() == 0

    monkeypatch.setattr(router, "_consumer_pending", 0)
    assert (await client.post("/consumer/scans/image", files=_files())).status_code == 201
    assert router._consumer_pending == 0

    undecodable = await client.post(
        "/consumer/scans/image", files={"image": ("x.jpg", b"not an image", "image/jpeg")}
    )
    assert undecodable.status_code == 422
    assert router._consumer_pending == 0
