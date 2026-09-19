"""Civic planning routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.schemas.government import GovernmentSummaryResponse
from app.services.government_service import build_government_summary

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

