"""HTTP contract tests for the exported analytics router."""

from datetime import UTC, datetime

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts import DeclarationField, FieldState
from app.core import Jurisdiction, Principal, RoleTier, create_access_token, get_session
from app.modules.analytics.router import analytics_router

from .test_repository import add_scan_with_verdict

pytestmark = pytest.mark.postgres

ROUTES = (
    "/analytics/by-rule",
    "/analytics/by-category",
    "/analytics/over-time",
    "/analytics/jurisdiction",
)

CONTROLLER = Principal(
    subject="controller-mh", tier=RoleTier.STATE, jurisdiction=Jurisdiction(state="Maharashtra")
)
OTHER_STATE = Principal(
    subject="controller-ka", tier=RoleTier.STATE, jurisdiction=Jurisdiction(state="Karnataka")
)


def auth(principal: Principal) -> dict[str, str]:
    """A bearer header carrying a genuinely signed token for ``principal``."""
    return {"Authorization": f"Bearer {create_access_token(principal)}"}


@pytest_asyncio.fixture
async def client(session: AsyncSession) -> AsyncClient:
    """Serve the router with the test's real PostgreSQL session dependency."""
    application = FastAPI()
    application.include_router(analytics_router)

    async def session_override():
        """Yield the transactionless read session used by this request."""
        yield session

    application.dependency_overrides[get_session] = session_override
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://analytics.test") as http:
        yield http


async def test_category_endpoint_returns_typed_unconfirmed_bucket(
    client: AsyncClient, session: AsyncSession
) -> None:
    """The API presents a missing confirmed category without writing or inferring one."""
    timestamp = datetime(2026, 9, 8, 9, tzinfo=UTC)
    for _ in range(3):
        await add_scan_with_verdict(
            session,
            created_at=timestamp,
            evaluated_at=timestamp,
            product_category=None,
        )

    response = await client.get("/analytics/by-category", headers=auth(CONTROLLER))

    assert response.status_code == 200, response.text
    assert response.json() == [{"product_category": "UNCONFIRMED", "count": 3}]


async def test_rule_endpoint_returns_distinct_failing_scan_cohort(
    client: AsyncClient, session: AsyncSession
) -> None:
    """The API exposes one rule cell for the eligible distinct-scan cohort."""
    timestamp = datetime(2026, 9, 8, 9, tzinfo=UTC)
    for _ in range(3):
        await add_scan_with_verdict(
            session,
            created_at=timestamp,
            evaluated_at=timestamp,
            findings=(
                ("RULE-API", FieldState.FAIL, DeclarationField.NET_QUANTITY),
                ("RULE-PASS-ONLY", FieldState.PASS, DeclarationField.RETAIL_SALE_PRICE),
            ),
        )

    response = await client.get("/analytics/by-rule", headers=auth(CONTROLLER))

    assert response.status_code == 200, response.text
    assert response.json() == [{"rule_id": "RULE-API", "count": 3}]


async def test_over_time_endpoint_uses_evaluation_day(
    client: AsyncClient, session: AsyncSession
) -> None:
    """The API buckets eligible cohorts by verdict evaluation time rather than scan creation."""
    created_at = datetime(2026, 9, 1, 23, tzinfo=UTC)
    evaluated_at = datetime(2026, 9, 8, 1, tzinfo=UTC)
    for _ in range(3):
        await add_scan_with_verdict(
            session,
            created_at=created_at,
            evaluated_at=evaluated_at,
        )

    response = await client.get("/analytics/over-time", headers=auth(CONTROLLER))

    assert response.status_code == 200, response.text
    assert response.json() == [{"day": "2026-09-08", "count": 3}]


async def test_jurisdiction_endpoint_returns_density_after_suppression(
    client: AsyncClient, session: AsyncSession
) -> None:
    """The API emits density only for privacy-eligible jurisdiction cells."""
    timestamp = datetime(2026, 9, 8, 9, tzinfo=UTC)
    for _ in range(3):
        await add_scan_with_verdict(
            session,
            district="Satara",
            created_at=timestamp,
            evaluated_at=timestamp,
        )
    for _ in range(2):
        await add_scan_with_verdict(
            session,
            district="Pune",
            created_at=timestamp,
            evaluated_at=timestamp,
        )

    response = await client.get("/analytics/jurisdiction", headers=auth(CONTROLLER))

    assert response.status_code == 200, response.text
    assert response.json() == [
        {
            "state": "Maharashtra",
            "region": "Pune",
            "district": "Satara",
            "count": 3,
            "density_band": "MEDIUM",
        }
    ]


@pytest.mark.parametrize("route", ROUTES)
async def test_every_analytics_route_refuses_an_unauthenticated_caller(
    client: AsyncClient, session: AsyncSession, route: str
) -> None:
    """No token, no aggregate — with eligible data present, so a 401 is not an empty 200."""
    timestamp = datetime(2026, 9, 8, 9, tzinfo=UTC)
    for _ in range(3):
        await add_scan_with_verdict(session, created_at=timestamp, evaluated_at=timestamp)

    response = await client.get(route)

    assert response.status_code == 401, response.text


@pytest.mark.parametrize("route", ROUTES)
async def test_an_officer_of_another_state_sees_no_cell(
    client: AsyncClient, session: AsyncSession, route: str
) -> None:
    """An authenticated officer outside the jurisdiction gets an empty aggregate."""
    timestamp = datetime(2026, 9, 8, 9, tzinfo=UTC)
    for _ in range(3):
        await add_scan_with_verdict(
            session,
            created_at=timestamp,
            evaluated_at=timestamp,
            findings=(("RULE-API", FieldState.FAIL, DeclarationField.NET_QUANTITY),),
        )

    assert (await client.get(route, headers=auth(CONTROLLER))).json() != []
    response = await client.get(route, headers=auth(OTHER_STATE))

    assert response.status_code == 200, response.text
    assert response.json() == []
