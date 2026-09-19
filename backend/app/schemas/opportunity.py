"""Evidence-backed business opportunity context schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.evidence import Evidence


class OpportunityIndicator(BaseModel):
    key: str
    label: str
    value: float | None
    unit: str | None = None
    evidence: list[Evidence] = Field(default_factory=list)


class OpportunityResponse(BaseModel):
    category: str
    competition_count: int
    total_businesses: int
    indicators: list[OpportunityIndicator] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
