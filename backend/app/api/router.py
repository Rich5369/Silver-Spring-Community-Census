"""Aggregate router.

Every route module is registered here and the result is mounted once in
:mod:`app.main`.

Note on prefixes: routes are mounted at the application root, with no ``/api``
or ``/v1`` segment. The frontend's endpoint table in ``src/services/api.js``
calls bare paths such as ``/businesses`` against ``VITE_API_BASE_URL``, so
matching that exactly means the frontend needs no change to talk to us.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import health

api_router = APIRouter()
api_router.include_router(health.router)
