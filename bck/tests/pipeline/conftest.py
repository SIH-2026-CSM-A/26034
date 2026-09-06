"""Fixtures for the scan endpoints: a real database, a real app, real tokens.

Postgres-marked for the same reason ``tests/persistence`` is — these exercise the async
engine, the ``jsonb`` findings column and the native enum types, none of which SQLite
stands in for honestly. They skip when ``DATABASE_URL`` is unset so a laptop still gets a
clean run, and CI provides Postgres, which is what stops them being a permanent skip.

**No lifespan runs here.** The app's lifespan verifies the vision model weights and
refuses to start without them; the endpoints under test are the catalogue path and the
reads, which touch no model. Driving the app through ``ASGITransport`` exercises the
routes, the dependencies and the middleware without that check. The check itself is tested
directly in ``tests/core/test_startup.py`` rather than being smuggled in here.

**Tokens are minted, not typed.** :func:`~app.core.auth.create_access_token` signs a real
token for a real principal, so the routes go through the same verification a browser would
trigger. Nothing here configures ``OFFICERS``: what is under test is authorisation, not
the password flow.
"""

import os
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.core.config import Settings, get_settings
from app.core.db import dispose_engine, get_session
from app.core.rbac import Jurisdiction, Principal, RoleTier
from app.core.schema import Base

JWT_SECRET = "test-signing-key-not-used-anywhere-real"

INSPECTOR = Principal(
    subject="inspector-satara",
    tier=RoleTier.DISTRICT,
    jurisdiction=Jurisdiction(state="Maharashtra", region="Pune", district="Satara"),
)
"""A district officer. The narrowest tier, and the one that does the inspecting."""

OTHER_INSPECTOR = Principal(
    subject="inspector-mysuru",
    tier=RoleTier.DISTRICT,
    jurisdiction=Jurisdiction(state="Karnataka", region="Mysuru", district="Mysuru"),
)
"""A district officer in another state entirely. Everything the first one files is
invisible to this one, and must not merely be forbidden to them."""

CONTROLLER = Principal(
    subject="controller-mh",
    tier=RoleTier.STATE,
    jurisdiction=Jurisdiction(state="Maharashtra"),
)
"""A state officer whose authority contains the district officer's."""


@pytest.fixture
def configured(monkeypatch: pytest.MonkeyPatch) -> str:
    """Settings pointed at the test database, with a developer's own .env ignored."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL is not set; the scan endpoints need a database")
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("JWT_SECRET", JWT_SECRET)
    monkeypatch.delenv("OFFICERS", raising=False)
    get_settings.cache_clear()
    return url


@pytest_asyncio.fixture
async def schema(configured: str) -> AsyncIterator[None]:
    """A schema built from the metadata and torn down after.

    ``create_all`` rather than the migration on purpose: what the migration produces is
    proved in ``tests/persistence``, and repeating it here would make every endpoint test
    fail for a migration's reasons.
    """
    from app.core.db import get_engine

    engine = get_engine()
    async with engine.begin() as connection:
        await _clean(connection)
        await connection.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as connection:
        await _clean(connection)
    await dispose_engine()
    get_settings.cache_clear()


async def _clean(connection) -> None:
    """Leave the database genuinely empty, ``alembic_version`` included.

    Dropping only the mapped tables leaves that one behind still stamped at head, and
    ``tests/persistence`` would then try to downgrade a schema that is not there — failing
    on an index it cannot drop, several tests away from the suite that actually caused it.
    These two suites share whatever ``DATABASE_URL`` points at, so each has to hand it back
    in the state it borrowed it in.
    """
    await connection.run_sync(Base.metadata.drop_all)
    await connection.execute(text("drop table if exists alembic_version"))


@pytest_asyncio.fixture
async def client(schema: None) -> AsyncIterator[AsyncClient]:
    """The real application, driven over ASGI, sharing the test's database."""
    from app.main import create_app

    application = create_app()
    application.dependency_overrides[get_session] = get_session
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://pccs.test") as http:
        yield http


def auth(principal: Principal) -> dict[str, str]:
    """A bearer header carrying a genuinely signed token for ``principal``."""
    from app.core.auth import create_access_token

    return {"Authorization": f"Bearer {create_access_token(principal)}"}


def dsn_name(url: str) -> str:
    """The database a failure message should name, without its password."""
    return make_url(url).render_as_string()
