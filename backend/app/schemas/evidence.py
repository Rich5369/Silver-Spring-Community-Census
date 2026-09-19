"""Shared provenance schema.

Every data-derived value the API returns carries one of these. It is a
separate module because both metric responses and GeoJSON features cite the
same way.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Evidence(BaseModel):
    """Where a value came from."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "dataset": "American Community Survey 5-Year Estimates (2024)",
                "dataset_year": 2024,
                "source_variable": "B19013_001E",
                "source_url": "https://api.census.gov/data/2024/acs/acs5",
                "organization": "US Census Bureau",
            }
        }
    )

    dataset: str = Field(description="Dataset name and release.")
    dataset_year: int | None = Field(
        default=None,
        description="Release year. Null for continuously-edited sources such as OSM.",
    )
    source_variable: str | None = Field(
        default=None,
        description=(
            "The provider's variable for this value, e.g. 'B19013_001E'. For a "
            "derived metric this is the full formula, so the number can be "
            "reproduced from the published tables."
        ),
    )
    source_url: str = Field(description="Citable URL for the dataset.")
    organization: str = Field(description="Publishing organization.")


class ErrorResponse(BaseModel):
    """Body returned with a 4xx response."""

    model_config = ConfigDict(
        json_schema_extra={"example": {"detail": "No area found with GEOID '24031999999'."}}
    )

    detail: str
