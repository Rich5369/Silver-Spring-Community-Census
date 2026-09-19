"""Civic-facing summary schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.insights import InsightsResponse


class GovernmentSummaryResponse(BaseModel):
    """Evidence-backed context for local government and civic planning."""

    audience: str = "local government and community planning"
    study_area: InsightsResponse
    available_views: list[str] = Field(default_factory=list)
    unavailable_views: list[str] = Field(default_factory=list)
    recommended_uses: list[str] = Field(default_factory=list)
    data_gaps: list[str] = Field(default_factory=list)
