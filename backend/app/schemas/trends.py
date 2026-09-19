from __future__ import annotations

from pydantic import BaseModel, Field


class TrendPoint(BaseModel):
    year: int
    value: float


class TrendSeries(BaseModel):
    key: str
    label: str
    unit: str
    points: list[TrendPoint] = Field(default_factory=list)


class GovernmentTrendsResponse(BaseModel):
    years: list[int] = Field(default_factory=list)
    series: list[TrendSeries] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)

