"""Version 1 API router.

Mounted at ``/api/v1``. The unversioned routes that predate this prefix are
still served for backwards compatibility - see ``app.api.router``.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import areas, businesses, insights, map as map_routes

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(areas.router)
v1_router.include_router(businesses.router)
v1_router.include_router(map_routes.router)
v1_router.include_router(insights.router)
