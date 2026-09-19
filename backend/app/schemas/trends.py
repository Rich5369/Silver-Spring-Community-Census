from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class TrendPoint(BaseModel):
    """One observation in a trend series.

    A series is either additive or not, and the two cases carry different
    fields. ``value`` holds a summable total; ``low``/``high`` hold the range
    across the study-area tracts for a metric that cannot be summed. Exactly
    one of the two forms is populated, and ``TrendSeries.basis`` says which.
    """

    year: int
    value: float | None = None
    low: float | None = None
    high: float | None = None


class TrendSource(BaseModel):
    """Provenance for a whole series, assembled from the rows behind it."""

    organization: str
    dataset: str
    #: ACS variable or formula the stored metric was computed from.
    table: str
    #: Per-release source URLs, newest last, parallel to ``years``.
    urls: list[str] = Field(default_factory=list)
    years: list[int] = Field(default_factory=list)
    tract_count: int = 0


class TrendSeries(BaseModel):
    key: str
    label: str
    unit: str
    #: "total" -> points carry ``value``; "range" -> points carry ``low``/``high``.
    basis: Literal["total", "range"] = "total"
    points: list[TrendPoint] = Field(default_factory=list)
    source: TrendSource | None = None
    #: Why this series is shaped the way it is, shown alongside the chart.
    method: str | None = None


class GovernmentTrendsResponse(BaseModel):
    years: list[int] = Field(default_factory=list)
    series: list[TrendSeries] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
