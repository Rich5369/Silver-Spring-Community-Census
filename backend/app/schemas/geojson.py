"""GeoJSON response schemas (RFC 7946).

Typed rather than raw dicts so the response shape is validated on the way
out and documented in the OpenAPI schema the frontend reads.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

#: Geometry types RFC 7946 permits for an area boundary.
POLYGON_TYPES: frozenset[str] = frozenset({"Polygon", "MultiPolygon"})


class Geometry(BaseModel):
    """A GeoJSON geometry object."""

    type: str
    coordinates: list[Any]


class MetricEvidence(BaseModel):
    """The citation behind one metric value.

    Carried per metric rather than per feature because a feature's values can
    come from different datasets or vintages.
    """

    dataset: str
    dataset_year: int | None = None
    source_variable: str | None = None
    source_url: str
    organization: str


class MetricValue(BaseModel):
    """One metric, inseparable from its evidence."""

    value: float | None
    unit: str | None = None
    evidence: MetricEvidence


class FeatureProperties(BaseModel):
    """Properties attached to each geography feature.

    ``geoid`` is the stable join key. The frontend should key off it rather
    than ``name``: tract names are neither unique nor stable across vintages.
    """

    geoid: str
    name: str
    geography_type: str
    state_fips: str | None = None
    county_fips: str | None = None
    tract_code: str | None = None
    #: Provenance for the boundary itself, distinct from the metrics'.
    boundary_source: MetricEvidence | None = None
    metrics: dict[str, MetricValue] = Field(default_factory=dict)


class Feature(BaseModel):
    """A GeoJSON Feature."""

    type: Literal["Feature"] = "Feature"
    #: Duplicated from properties.geoid: RFC 7946 allows a top-level id, and
    #: Leaflet exposes it directly on the layer.
    id: str
    geometry: Geometry
    properties: FeatureProperties


class FeatureCollection(BaseModel):
    """A GeoJSON FeatureCollection."""

    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[Feature] = Field(default_factory=list)
