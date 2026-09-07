"""PostgreSQL fixtures for the reviews module tests."""

import asyncio
import os
import sys
from collections.abc import AsyncIterator, Callable, Iterator
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core import ProductReviewRow
from app.core.config import Settings, get_settings

JWT_SECRET = "test-signing-key-not-used-anywhere-real"


def pytest_asyncio_loop_factories(
    config: pytest.Config, item: pytest.Item
) -> dict[str, Callable[[], asyncio.AbstractEventLoop]]:
    """Provide the selector event loop required by psycopg on Windows."""
    del config, item
    if sys.platform == "win32":
        return {"windows-selector": asyncio.SelectorEventLoop}
    return {"default": asyncio.new_event_loop}


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Keep a developer's local settings out of reviews database tests."""
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    monkeypatch.setenv("JWT_SECRET", JWT_SECRET)
    monkeypatch.delenv("PCCS_REVIEW_PUBLICATION_THRESHOLD", raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def configured(monkeypatch: pytest.MonkeyPatch) -> str:
    """Return a local PostgreSQL DSN or skip database behavior tests."""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.fail("DATABASE_URL is not set; reviews persistence needs PostgreSQL")
    database_config = make_url(database_url)
    if database_config.drivername != "postgresql+psycopg" or database_config.host not in {
        "localhost",
        "127.0.0.1",
        "::1",
    }:
        pytest.fail("reviews tests require a local postgresql+psycopg DATABASE_URL")
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    return database_url


@pytest_asyncio.fixture
async def schema(configured: str) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """Create and remove one generated PostgreSQL schema around one test."""
    schema_name = f"reviews_test_{uuid4().hex}"
    engine = create_async_engine(
        configured,
        connect_args={"options": f"-csearch_path={schema_name},public"},
        pool_pre_ping=True,
    )
    async with engine.begin() as connection:
        await connection.execute(text(f'create schema "{schema_name}"'))
        await connection.run_sync(ProductReviewRow.__table__.create, checkfirst=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    async with engine.begin() as connection:
        await connection.execute(text(f'drop schema "{schema_name}" cascade'))
    await engine.dispose()


@pytest_asyncio.fixture
async def session(schema: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
    """Provide one real async PostgreSQL session for a focused persistence test."""
    async with schema() as database_session:
        yield database_session


@pytest.fixture
def session_factory(
    schema: async_sessionmaker[AsyncSession],
) -> async_sessionmaker[AsyncSession]:
    """Provide a factory for separate request-equivalent PostgreSQL sessions."""
    return schema
