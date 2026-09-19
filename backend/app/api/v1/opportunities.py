"""Transparent, non-predictive business context routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.integrations.osm_categories import BUSINESS_CATEGORIES
from app.schemas.opportunity import OpportunityResponse
from app.services.opportunity_service import build_opportunity_context

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


@router.get("", response_model=OpportunityResponse, summary="Evidence-backed business context")
def opportunity_context(
    category: str = Query(
        ..., description="Business taxonomy category, such as Cafe or Restaurant.", examples=["Cafe"]
    ),
    session: Session = Depends(get_session),
) -> OpportunityResponse:
    """Return competition and stored community indicators without scoring."""
    normalized = next((item for item in BUSINESS_CATEGORIES if item.lower() == category.lower()), category)
    return build_opportunity_context(session, normalized)
