"""The application entrypoint: the FastAPI instance ``uvicorn app.main:app`` serves.

Everything below the routers is composed elsewhere. This file mounts, configures and
checks, and holds no business logic of any kind — a rule is never decided here.

**Startup fails loudly rather than late.** :func:`lifespan` verifies the vision model
weights before the application serves anything, and refuses to start when one is missing.
Weights are gitignored and pre-cached, so the case this guards is a fresh clone or a
machine that never fetched them, and the alternative is a ``FileNotFoundError`` surfacing
as a 500 on the first scan an officer submits. A stage that cannot run must stop the
application starting; it must never fall back to a different stage, because a verdict
produced by a path nobody chose is worse than no verdict.

The database is deliberately *not* opened at startup. :func:`~app.core.db.get_engine` is
``lru_cache``d and raises with a message naming ``DATABASE_URL`` on first use, so building
it here would only move that failure earlier while opening a connection pool in every test
that imports this module. Shutdown is different: the pool has to be closed, and that is
what the second half of the lifespan is for.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core import auth_router, dispose_engine, get_settings
from app.modules.analytics.router import analytics_router
from app.modules.complaints.router import complaints_router
from app.modules.reviews.router import reviews_router
from app.modules.vendor.router import vendor_router
from app.pipeline.router import consumer_router, scan_router

API_TITLE = "PCCS — Packaged Commodity Compliance System"
API_DESCRIPTION = (
    "Compliance decision support under the Legal Metrology (Packaged Commodities) Rules, "
    "2011. Every outcome is a recommendation for a Legal Metrology officer to examine. "
    "Nothing this API returns is a finding of contravention, and a human confirmation "
    "step sits between any output and any enforcement action."
)

ALLOWED_METHODS = ("GET", "POST", "OPTIONS")
"""The methods the officer surface actually uses. Listed rather than wildcarded: a scan
path that is append-only in its schema should not advertise PUT and DELETE."""

ALLOWED_HEADERS = ("Authorization", "Content-Type")
"""Authorization for the bearer token, Content-Type for JSON and multipart uploads."""


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Check what the application cannot run without, then clean up the pool on the way out."""
    missing = get_settings().missing_model_paths()
    if missing:
        raise RuntimeError(
            "the following model paths are unset or do not exist on disk: "
            f"{', '.join(missing)}. Model weights are gitignored and must be pre-cached "
            "locally — see bck/.env.example. The application will not start without them, "
            "because a vision stage that cannot run must not become a 500 on an officer's "
            "first scan."
        )
    logging.getLogger(__name__).info("model weights verified; PCCS is starting")
    yield
    await dispose_engine()


def create_app() -> FastAPI:
    """Build the application.

    A function rather than module-level statements so a test can build a second instance
    with different settings without re-importing this module, and so the import of
    ``app.main`` itself does nothing observable.
    """
    application = FastAPI(
        title=API_TITLE,
        description=API_DESCRIPTION,
        version="0.1.0",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        # The Vite dev origin and nothing else by default. Credentials are allowed, and a
        # wildcard origin with credentials is both refused by browsers and wrong here: the
        # officer surface is the only thing that should be calling this API.
        allow_origins=list(get_settings().cors_origins),
        allow_credentials=True,
        allow_methods=list(ALLOWED_METHODS),
        allow_headers=list(ALLOWED_HEADERS),
    )
    application.include_router(auth_router)
    application.include_router(scan_router)
    application.include_router(consumer_router)
    application.include_router(reviews_router)
    application.include_router(analytics_router)
    application.include_router(complaints_router)
    application.include_router(vendor_router)
    return application


app = create_app()
"""What ``uvicorn app.main:app`` serves."""
