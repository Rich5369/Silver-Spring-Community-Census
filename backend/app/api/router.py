"""Aggregate router.

Two surfaces are mounted:

* ``/api/v1/...`` - the versioned API (:mod:`app.api.v1.router`).
* unversioned ``/health``, ``/businesses``, ``/geographies`` - the original
  bare paths the frontend's ``ENDPOINTS`` table in ``src/services/api.js``
  already calls. They are kept so the frontend keeps working unchanged while
  it migrates to the ``/api/v1`` prefix, and can be removed once it has.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import businesses, geographies, health
from app.api.v1.router import v1_router

api_router = APIRouter()

# Versioned surface.
api_router.include_router(v1_router)

# Legacy unversioned surface, excluded from the docs so the schema the
# frontend reads shows one clear contract.
api_router.include_router(health.router)
api_router.include_router(businesses.router, include_in_schema=False)
api_router.include_router(geographies.router, include_in_schema=False)
