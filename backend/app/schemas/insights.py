"""Insight response schemas.

Three things are kept structurally separate so a reader can always tell them
apart:

* **source data** - values read from the database, each with evidence;
* **derivations** - how a computed number was produced, naming its
  numerator, denominator and contributing metrics;
* **observations** - factual statements about the data.

Observations describe what the dataset contains. They never recommend an
action and never assert causation.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.evidence import Evidence


class Coverage(BaseModel):
    """How much of the study area a figure is based on."""

    tracts_with_data: int
    tracts_total: int
    complete: bool = Field(
        description="False when at least one tract lacked the underlying metric."
    )


class Derivation(BaseModel):
    """How a computed value was produced."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "method": "ratio",
                "formula": "sum(renter_occupied_households) / sum(occupied_housing_units) * 100",
                "numerator_metrics": ["renter_occupied_households"],
                "denominator_metric": "occupied_housing_units",
                "numerator_value": 4132.0,
                "denominator_value": 7890.0,
            }
        }
    )

    method: str = Field(
        description="One of: direct, sum, ratio, range. How the value was computed."
    )
    formula: str = Field(description="Human-readable formula, reproducible by hand.")
    numerator_metrics: list[str] = Field(default_factory=list)
    denominator_metric: str | None = None
    numerator_value: float | None = None
    denominator_value: float | None = None


class SnapshotValue(BaseModel):
    """One figure in the community snapshot.

    ``available`` is explicit. When it is false, ``value`` is null and
    ``unavailable_reason`` says why - the figure is never estimated or
    filled in.
    """

    key: str
    label: str
    value: float | None = None
    unit: str | None = None
    available: bool
    unavailable_reason: str | None = None
    derivation: Derivation | None = None
    coverage: Coverage | None = None
    evidence: list[Evidence] = Field(default_factory=list)


class ValueRange(BaseModel):
    """A minimum and maximum across tracts, used where a total is meaningless."""

    key: str
    label: str
    minimum: float | None = None
    maximum: float | None = None
    unit: str | None = None
    available: bool
    unavailable_reason: str | None = None
    coverage: Coverage | None = None
    evidence: list[Evidence] = Field(default_factory=list)


class CategoryBreakdown(BaseModel):
    """One business category and its share of the mapped total."""

    category: str
    count: int
    share_of_total: float = Field(description="Percent of all mapped businesses.")


class BusinessLandscape(BaseModel):
    """What the business dataset contains."""

    total_businesses: int
    category_count: int
    categories: list[CategoryBreakdown] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)


class Observation(BaseModel):
    """A factual statement derived deterministically from stored data.

    Statements describe the dataset. They do not recommend actions, and they
    do not assert cause and effect.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "largest_business_category",
                "statement": (
                    "Restaurant is the largest business category in the current "
                    "dataset, with 77 of 207 mapped establishments (37.2%)."
                ),
                "topic": "business_landscape",
                "basis_metrics": ["business_category_counts"],
                "derivation": {
                    "method": "ratio",
                    "formula": "count(category = 'Restaurant') / count(all businesses) * 100",
                    "numerator_value": 77.0,
                    "denominator_value": 207.0,
                },
                "evidence": [],
            }
        }
    )

    id: str = Field(description="Stable identifier for this observation type.")
    statement: str = Field(description="Factual sentence about the stored data.")
    topic: str
    basis_metrics: list[str] = Field(
        default_factory=list, description="Metric keys the statement is computed from."
    )
    derivation: Derivation | None = None
    evidence: list[Evidence] = Field(default_factory=list)


class StudyArea(BaseModel):
    """What "Fenton Village" means here, stated explicitly."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Fenton Village, Silver Spring, Maryland",
                "tract_count": 14,
                "tract_geoids": ["24031701701", "24031701800"],
                "method": (
                    "Fenton Village is a commercial district with no Census "
                    "geography. Figures are aggregated from the Census tracts "
                    "intersecting a project-defined bounding box over downtown "
                    "Silver Spring, and are approximations of the district "
                    "rather than published estimates for it."
                ),
            }
        }
    )

    name: str
    tract_count: int
    tract_geoids: list[str] = Field(default_factory=list)
    method: str = Field(
        description="How the area was defined and what that implies for the figures."
    )


class UnavailableItem(BaseModel):
    """Something explicitly not reported, and why."""

    key: str
    reason: str


class InsightsResponse(BaseModel):
    """Deterministic summary of the stored data for one study area."""

    study_area: StudyArea
    community_snapshot: list[SnapshotValue] = Field(default_factory=list)
    ranges: list[ValueRange] = Field(default_factory=list)
    business_landscape: BusinessLandscape
    observations: list[Observation] = Field(default_factory=list)
    unavailable: list[UnavailableItem] = Field(default_factory=list)
