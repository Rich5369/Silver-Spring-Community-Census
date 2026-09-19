"""Civic-facing summary schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.evidence import Evidence
from app.schemas.insights import InsightsResponse


class CivicPriority(BaseModel):
    """A bounded, evidence-backed planning signal—not a prediction."""

    key: str
    priority: str
    signal: str
    why_it_matters: str
    next_step: str
    evidence: list[Evidence] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class ServiceRequestTrend(BaseModel):
    """Annual official 311 volume for the study-area ZIP code."""

    year: int
    requests: int


class ServiceRequestResponse(BaseModel):
    dataset: str
    geography: str
    series: list[ServiceRequestTrend] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    source_status: str = "live"


class GovernmentSummaryResponse(BaseModel):
    """Evidence-backed context for local government and civic planning."""

    audience: str = "local government and community planning"
    study_area: InsightsResponse
    available_views: list[str] = Field(default_factory=list)
    unavailable_views: list[str] = Field(default_factory=list)
    recommended_uses: list[str] = Field(default_factory=list)
    data_gaps: list[str] = Field(default_factory=list)
    priorities: list[CivicPriority] = Field(default_factory=list)
