"""The engine, the session factory, and the one dependency that hands out a session.

**Scope: one session per request.** A session is a unit of work and an identity map.
Sharing one across requests would share uncommitted state between two officers, so
:func:`get_session` opens one, yields it to exactly one handler, and closes it on the
way out. ``Depends(get_session)`` is the only handle a handler gets — there is no
module-level session object and no engine created at import time.

**The dependency does not commit.** It rolls back and closes; committing is the
caller's. A teardown-commit fires *after* the response body has been built, so a failure
at commit cannot change the status code the client already received, and it commits work
a handler may have decided to abandon. The transaction boundary belongs where the
business decision is.

**One DSN string serves both modes.** ``postgresql+psycopg://`` is valid for
:func:`~sqlalchemy.create_engine` and :func:`~sqlalchemy.ext.asyncio.create_async_engine`
alike — SQLAlchemy picks sync or async from the constructor, not from the URL. The app
runs async here and Alembic runs the same string synchronously in ``alembic/env.py``,
with no rewriting between them and no second setting to keep in step.

The ceiling: nothing here applies :func:`app.core.rbac.scope_to_jurisdiction`. A query
that never passes through that function is not scoped, and no check in this module will
notice. Closing that properly means a repository layer owning the session; there is no
caller for one yet.
"""

from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    """The process-wide async engine, built on first use.

    Cached rather than module-level for two reasons: importing ``app.core`` opens no
    connection pool, and a deployment that never set ``DATABASE_URL`` fails here with a
    message naming the setting instead of somewhere deep in a request.

    ``pool_pre_ping`` is on. The demo runs on a laptop that sleeps, and without it the
    first request after the lid closes dies on a connection the pool still believes in.
    """
    database_url = get_settings().database_url
    if database_url is None:
        raise RuntimeError(
            "DATABASE_URL is not set; the application cannot open a database connection. "
            "See bck/.env.example."
        )
    return create_async_engine(database_url, pool_pre_ping=True)


@lru_cache(maxsize=1)
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """The session factory bound to :func:`get_engine`.

    ``expire_on_commit=False`` is not a convenience. With it left on, reading an
    attribute off an instance after a commit triggers a lazy refresh outside greenlet
    context and raises ``MissingGreenlet`` — normally while the response is being
    serialised, a long way from the commit that caused it.
    """
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: a session for the duration of one request.

    Put this on every endpoint that touches the database. The caller commits; this
    rolls back and closes whatever the caller did not.
    """
    async with get_session_factory()() as session:
        yield session


async def dispose_engine() -> None:
    """Close the pool and drop both cached factories.

    For application shutdown and for tests that swap the DSN between cases. Without it
    a replaced engine leaves its connections open until the process ends.
    """
    if get_engine.cache_info().currsize:
        await get_engine().dispose()
    get_session_factory.cache_clear()
    get_engine.cache_clear()
