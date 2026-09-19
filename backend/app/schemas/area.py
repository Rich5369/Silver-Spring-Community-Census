"""Area (geography) response schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.evidence import Evidence


class AreaOut(BaseModel):
    """One geographic area.

    ``geoid`` is the stable join key - the Census GEOID for Census
    geographies. Join on it, never on ``name``: tract names are neither
    unique nor stable across ACS vintages.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "geoid": "24031701701",
                "name": "Census Tract 7017.01; Montgomery County; Maryland",
                "geography_type": "tract",
                "state_fips": "24",
                "county_fips": "031",
                "tract_code": "701701",
                "has_boundary": True,
            }
        }
    )

    geoid: str = Field(description="Stable identifier. Use this as the join key.")
    name: str
    geography_type: str = Field(
        description="One of: state, county, tract, block_group, neighborhood."
    )
    state_fips: str | None = None
    county_fips: str | None = None
    tract_code: str | None = None
    has_boundary: bool = Field(
        description="Whether a GeoJSON boundary is stored for this area."
    )


class AreaListResponse(BaseModel):
    """A page of areas."""

    count: int = Field(description="Number of areas in this response.")
    areas: list[AreaOut] = Field(default_factory=list)


class MetricOut(BaseModel):
    """One metric value, inseparable from its evidence."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "metric_key": "median_household_income",
                "value": 111411.0,
                "unit": "usd",
                "evidence": {
                    "dataset": "American Community Survey 5-Year Estimates (2024)",
                    "dataset_year": 2024,
                    "source_variable": "B19013_001E",
                    "source_url": "https://api.census.gov/data/2024/acs/acs5",
                    "organization": "US Census Bureau",
                },
            }
        }
    )

    metric_key: str = Field(description="Stable internal name, e.g. 'total_population'.")
    value: float | None = Field(
        description=(
            "Null when the Census suppressed the estimate or it could not be "
            "computed. Null means 'not available', never zero."
        )
    )
    unit: str | None = Field(
        default=None, description="e.g. people, usd, years, percent, households."
    )
    evidence: Evidence


class AreaMetricsResponse(BaseModel):
    """Every metric recorded for one area."""

    area: AreaOut
    count: int
    metrics: list[MetricOut] = Field(default_factory=list)
