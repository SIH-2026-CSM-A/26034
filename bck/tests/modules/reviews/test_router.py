"""HTTP contracts for the anonymous review router."""

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core import ConsumerSafetyClaim, get_session
from app.modules.reviews import service
from app.modules.reviews.router import reviews_router

pytestmark = pytest.mark.postgres


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Serve the router with a harmless session dependency for HTTP-only tests."""
    application = FastAPI()
    application.include_router(reviews_router)

    class Transaction:
        """Minimal async transaction context for HTTP-only route tests."""

        async def __aenter__(self) -> "Transaction":
            """Enter the harmless transaction context."""
            return self

        async def __aexit__(self, *args: object) -> None:
            """Exit the harmless transaction context."""
            del args

    class SessionStub:
        """Minimal session surface exercised by the router."""

        def begin(self) -> Transaction:
            """Return the harmless transaction context."""
            return Transaction()

    async def session_override() -> AsyncIterator[AsyncSession]:
        """Yield the session placeholder used by service stubs in this HTTP harness."""
        yield SessionStub()  # type: ignore[misc]

    application.dependency_overrides[get_session] = session_override
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://reviews.test") as http:
        yield http


@pytest_asyncio.fixture
async def real_client(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncClient]:
    """Serve the router against real PostgreSQL sessions for an integration check."""
    application = FastAPI()
    application.include_router(reviews_router)

    async def session_override() -> AsyncIterator[AsyncSession]:
        """Yield one real session for each HTTP request."""
        async with session_factory() as session:
            yield session

    application.dependency_overrides[get_session] = session_override
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://reviews.test") as http:
        yield http


async def test_post_returns_held_without_hidden_metadata(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A below-threshold submission exposes only its neutral publication state."""

    async def record_submission(*args: object, **kwargs: object) -> bool:
        """Pretend the service held this submission for the HTTP mapping test."""
        del args, kwargs
        return False

    monkeypatch.setattr(service, "record_submission", record_submission)
    response = await client.post(
        "/reviews",
        json={
            "product_identifier": "  0012345678905  ",
            "consumer_safety_claim": "safe",
        },
    )

    assert response.status_code == 201, response.text
    assert response.json() == {
        "product_identifier": "0012345678905",
        "consumer_safety_claim": "safe",
        "publication_status": "HELD",
    }


async def test_post_returns_published_when_service_crosses_threshold(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A threshold-crossing submission exposes publication without row metadata."""

    async def record_submission(*args: object, **kwargs: object) -> bool:
        """Pretend the service published this submission for the HTTP mapping test."""
        del args, kwargs
        return True

    monkeypatch.setattr(service, "record_submission", record_submission)
    response = await client.post(
        "/reviews",
        json={
            "product_identifier": "8901234567890",
            "consumer_safety_claim": "unsafe",
        },
    )

    assert response.status_code == 201, response.text
    assert response.json() == {
        "product_identifier": "8901234567890",
        "consumer_safety_claim": "unsafe",
        "publication_status": "PUBLISHED",
    }


async def test_post_rejects_invalid_sentiment(client: AsyncClient) -> None:
    """The public route accepts only the existing SAFE and UNSAFE values."""
    response = await client.post(
        "/reviews",
        json={
            "product_identifier": "8901234567890",
            "consumer_safety_claim": "mostly_safe",
        },
    )

    assert response.status_code == 422


async def test_post_rejects_client_supplied_anonymous_token(client: AsyncClient) -> None:
    """The public route never accepts the persistence-only row token."""
    response = await client.post(
        "/reviews",
        json={
            "product_identifier": "8901234567890",
            "consumer_safety_claim": "safe",
            "anonymous_token": "client-supplied",
        },
    )

    assert response.status_code == 422


async def test_get_returns_only_published_aggregates(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The public read maps published core enum values to deterministic aggregates."""

    async def get_published_consensus(*args: object, **kwargs: object):
        """Return already-filtered published rows for the HTTP mapping test."""
        del args, kwargs
        return [
            (ConsumerSafetyClaim.SAFE, 3),
            (ConsumerSafetyClaim.UNSAFE, 4),
        ]

    monkeypatch.setattr(service, "get_published_consensus", get_published_consensus)
    response = await client.get("/reviews/8901234567890")

    assert response.status_code == 200, response.text
    assert response.json() == {
        "product_identifier": "8901234567890",
        "published_consensus": [
            {"consumer_safety_claim": "safe", "submission_count": 3},
            {"consumer_safety_claim": "unsafe", "submission_count": 4},
        ],
    }


async def test_get_returns_empty_aggregate_when_nothing_is_published(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An empty public result does not reveal whether held submissions exist."""

    async def get_published_consensus(*args: object, **kwargs: object):
        """Return no published rows for the HTTP privacy test."""
        del args, kwargs
        return []

    monkeypatch.setattr(service, "get_published_consensus", get_published_consensus)
    response = await client.get("/reviews/8901234567890")

    assert response.status_code == 200, response.text
    assert response.json() == {
        "product_identifier": "8901234567890",
        "published_consensus": [],
    }


async def test_real_http_submission_and_public_read_use_review_persistence(
    real_client: AsyncClient,
) -> None:
    """Real HTTP requests publish a cohort and expose only its aggregate."""
    responses = [
        await real_client.post(
            "/reviews",
            json={
                "product_identifier": "8901234567890",
                "consumer_safety_claim": "safe",
            },
        )
        for _ in range(3)
    ]

    assert [response.json()["publication_status"] for response in responses] == [
        "HELD",
        "HELD",
        "PUBLISHED",
    ]
    public_response = await real_client.get("/reviews/8901234567890")

    assert public_response.status_code == 200
    assert public_response.json() == {
        "product_identifier": "8901234567890",
        "published_consensus": [{"consumer_safety_claim": "safe", "submission_count": 3}],
    }
