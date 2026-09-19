"""FastAPI application entry point.

Run locally with::

    uvicorn app.main:app --reload --port 8000

from the ``backend/`` directory.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.database import init_database


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Prepare resources on startup and release them on shutdown."""
    init_database()
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and configure the FastAPI application.

    Exposed as a factory so tests can construct an isolated instance with
    overridden settings instead of mutating the module-level app.
    """
    settings = settings or get_settings()

    app = FastAPI(
        title="Silver Spring Community Intelligence API",
        description=(
            "Public-data community intelligence for Fenton Village, Silver "
            "Spring, Maryland. Every data-derived response carries the "
            "evidence behind it: dataset, year, geography, variable and source."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    # The frontend is served from a different origin (Vite on :5173) and calls
    # this API with absolute URLs, so CORS is required for any browser request
    # to succeed.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)
    return app


app = create_app()
