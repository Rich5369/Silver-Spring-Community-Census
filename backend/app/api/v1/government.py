"""Civic planning routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.schemas.government import GovernmentSummaryResponse, ServiceRequestResponse
from app.services.government_service import build_government_summary
from app.services.service_request_service import fetch_mc311_trend

router = APIRouter(prefix="/government", tags=["government"])


@router.get(
    "/summary",
    response_model=GovernmentSummaryResponse,
    summary="Evidence-backed civic planning summary",
)
def government_summary(
    session: Session = Depends(get_session),
) -> GovernmentSummaryResponse:
    """Expose current civic context and clearly mark unavailable trend views."""
    return build_government_summary(session)


@router.get("/service-requests", response_model=ServiceRequestResponse,
            summary="Official Montgomery County MC311 trend")
def service_requests() -> ServiceRequestResponse:
    """Return annual 311 volume for the ZIP containing the study area."""
    return fetch_mc311_trend()
