"""Service layer for health reporting.

Trivial today, but the endpoint stays a thin transport shim and the answer is
built here. That keeps the pattern consistent with the data endpoints to come,
where routers translate HTTP while services own the query and evidence logic.
"""

from __future__ import annotations

from app.core.config import Settings, get_settings
from app.schemas.health import HealthResponse


def get_health(settings: Settings | None = None) -> HealthResponse:
    """Build the liveness response.

    This reports that the process is up and serving. It deliberately does not
    touch the database: a liveness probe that fails when a dependency is
    degraded cannot distinguish "the API is down" from "the API is fine but
    the data is not", which is exactly what we need to tell apart during a
    live demo. A readiness check can be added separately if that becomes
    useful.
    """
    settings = settings or get_settings()
    return HealthResponse(status="ok", service=settings.service_name)
