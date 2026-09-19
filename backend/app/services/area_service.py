"""Area and metric query logic.

Route handlers delegate here; this module owns the mapping from ORM rows to
response schemas so no handler touches the database directly.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import CommunityMetric, Geography
from app.repositories import CommunityMetricRepository, GeographyRepository
from app.schemas.area import AreaMetricsResponse, AreaOut, MetricOut
from app.schemas.evidence import Evidence


def to_area(geography: Geography) -> AreaOut:
    """Map a geography row to its response schema."""
    return AreaOut(
        geoid=geography.geoid,
        name=geography.name,
        geography_type=geography.geography_type,
        state_fips=geography.state_fips,
        county_fips=geography.county_fips,
        tract_code=geography.tract_code,
        has_boundary=bool(geography.geometry_geojson),
    )


def to_metric(metric: CommunityMetric) -> MetricOut:
    """Map a metric row to its response schema, evidence included.

    Evidence is built here rather than being optional, so there is no code
    path that returns a value without its citation.
    """
    return MetricOut(
        metric_key=metric.metric_key,
        value=metric.value,
        unit=metric.unit,
        evidence=Evidence(
            dataset=metric.dataset,
            dataset_year=metric.dataset_year,
            source_variable=metric.source_variable,
            source_url=metric.source_url,
            organization=metric.data_source.organization,
        ),
    )


def list_areas(
    session: Session,
    *,
    geography_type: str | None = None,
    with_boundary_only: bool = False,
    limit: int | None = None,
) -> list[AreaOut]:
    """Filtered areas."""
    return [
        to_area(geography)
        for geography in GeographyRepository(session).list_areas(
            geography_type=geography_type,
            with_boundary_only=with_boundary_only,
            limit=limit,
        )
    ]


def get_area(session: Session, geoid: str) -> AreaOut | None:
    """One area by GEOID, or ``None`` if it has not been ingested."""
    geography = GeographyRepository(session).get_by_geoid(geoid)
    return to_area(geography) if geography else None


def get_area_metrics(session: Session, geoid: str) -> AreaMetricsResponse | None:
    """Every metric for one area, or ``None`` if the area is unknown.

    Returning ``None`` rather than an empty list lets the route distinguish
    "no such area" (404) from "this area has no metrics yet" (200 with an
    empty list) - a distinction that matters when debugging an integration.
    """
    geography = GeographyRepository(session).get_by_geoid(geoid)
    if geography is None:
        return None

    metrics = [
        to_metric(metric)
        for metric in CommunityMetricRepository(session).list_for_geography(
            geography.id
        )
    ]
    return AreaMetricsResponse(
        area=to_area(geography), count=len(metrics), metrics=metrics
    )
