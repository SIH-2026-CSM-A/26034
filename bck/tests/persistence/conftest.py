"""Fixtures for the tests that need a real PostgreSQL.

These are the only tests that exercise the migration, the ``jsonb`` columns, the native
enum types and the async engine behind :func:`app.core.db.get_session`. Everything in
``tests/core/test_persistence.py`` runs on SQLite and proves the mapping; this package
proves the parts that only exist on the deployment target.

They skip when ``DATABASE_URL`` is unset or nothing answers on it, so a laptop with
nothing running still gets a clean ``uv run pytest``. CI provides Postgres — that is what
keeps this package from being a permanently-skipped green tick.

**These tests own the database they point at.** The migration cycle downgrades to base,
which drops every table. Point ``DATABASE_URL`` at a scratch database.
"""

import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import psycopg
import pytest
from alembic.config import Config
from sqlalchemy.engine import make_url

from app.core.config import Settings, get_settings
from app.core.db import dispose_engine

JWT_SECRET = "test-signing-key-not-used-anywhere-real"
"""Required to construct :class:`Settings` at all. Nothing here exercises tokens."""

ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"
"""Resolved from this file, never from the working directory.

A relative path here would resolve against wherever pytest was started, and a config
that failed to load would take the tests with it — or worse, quietly find nothing.
"""

CONNECT_TIMEOUT_SECONDS = 3


def _reachable(url: str) -> bool:
    """Whether a server actually answers on ``url``."""
    libpq_url = make_url(url).set(drivername="postgresql").render_as_string(hide_password=False)
    try:
        with psycopg.connect(libpq_url, connect_timeout=CONNECT_TIMEOUT_SECONDS):
            return True
    except psycopg.Error:
        return False


@pytest.fixture
def database_url(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    """The configured DSN, or a skip naming why these tests did not run."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL is not set; nothing to migrate against")
    if not _reachable(url):
        pytest.skip(f"no PostgreSQL answering at {make_url(url).render_as_string()}")

    # A developer's own .env must not decide what these tests see, but DATABASE_URL is
    # exactly what the caller is pointing us at, so it is put back explicitly.
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("JWT_SECRET", JWT_SECRET)
    monkeypatch.delenv("OFFICERS", raising=False)
    get_settings.cache_clear()
    yield url
    get_settings.cache_clear()


@pytest.fixture
def alembic_config(database_url: str) -> Config:
    """Alembic configured exactly as the command line configures it.

    No ``sqlalchemy.url`` is set here for the same reason there is none in the ini file:
    ``alembic/env.py`` takes the DSN from ``app.core.config``, and a test that supplied
    its own would stop exercising that.
    """
    return Config(str(ALEMBIC_INI))


@pytest.fixture
async def engine_disposed() -> AsyncIterator[None]:
    """Close the async pool inside the test's own event loop.

    Disposing later, from a different loop, is how an async engine ends a test run with
    warnings about connections it can no longer reach.
    """
    yield
    await dispose_engine()
