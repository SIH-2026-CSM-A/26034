"""PostgreSQL fixtures for analytics repository tests."""

import asyncio
import os
import sys
from collections.abc import AsyncIterator, Callable, Iterator

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.core.config import Settings, get_settings
from app.core.db import dispose_engine, get_engine, get_session_factory
from app.core.schema import Base

JWT_SECRET = "test-signing-key-not-used-anywhere-real"


def pytest_asyncio_loop_factories(
    config: pytest.Config, item: pytest.Item
) -> dict[str, Callable[[], asyncio.AbstractEventLoop]]:
    """Provide the Windows selector loop required by psycopg's async driver."""
    del config, item
    if sys.platform == "win32":
        return {"windows-selector": asyncio.SelectorEventLoop}
    return {"default": asyncio.new_event_loop}


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Keep a developer's local environment out of analytics database tests."""
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    monkeypatch.setenv("JWT_SECRET", JWT_SECRET)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def configured(monkeypatch: pytest.MonkeyPatch) -> str:
    """Return the explicitly supplied PostgreSQL DSN or skip database behavior tests."""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is not set; analytics queries need PostgreSQL")
    database_config = make_url(database_url)
    if database_config.drivername != "postgresql+psycopg" or database_config.host not in {
        "localhost",
        "127.0.0.1",
        "::1",
    }:
        pytest.fail("analytics tests require a local postgresql+psycopg DATABASE_URL")
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    return database_url


@pytest_asyncio.fixture
async def schema(configured: str) -> AsyncIterator[None]:
    """Create and remove the complete mapped schema around an analytics test."""
    engine = get_engine()
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.execute(text("drop table if exists alembic_version"))
    await dispose_engine()


@pytest_asyncio.fixture
async def session(schema: None):
    """Provide one real async PostgreSQL session for a focused aggregate test."""
    async with get_session_factory()() as database_session:
        yield database_session
