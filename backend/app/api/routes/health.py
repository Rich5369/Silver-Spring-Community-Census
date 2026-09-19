"""Health check route."""

from __future__ import annotations

from fastapi import APIRouter

from app.schemas.health import HealthResponse
from app.services.health_service import get_health

router = APIRouter(tags=["system"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service liveness check",
)
def health() -> HealthResponse:
    """Report that the API process is up and serving requests."""
    return get_health()
