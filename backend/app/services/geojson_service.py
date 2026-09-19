"""Assemble GeoJSON from stored boundaries and metrics.

Reads only from the database. No external service is contacted while serving
a request, so a map render cannot fail because TIGERweb or the Census API is
slow or down.
"""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models import CommunityMetric, Geography
from app.repositories import (
    BusinessRepository,
    CommunityMetricRepository,
    GeographyRepository,
)
from app.schemas.geojson import (
    BusinessFeatureInfo,
    Feature,
    FeatureCollection,
    FeatureProperties,
    Geometry,
    MetricEvidence,
    MetricValue,
)
from app.schemas.map import CommunityMapResponse


def _evidence(metric: CommunityMetric) -> MetricEvidence:
    return MetricEvidence(
        dataset=metric.dataset,
        dataset_year=metric.dataset_year,
        source_variable=metric.source_variable,
        source_url=metric.source_url,
        organization=metric.data_source.organization,
    )


def _boundary_evidence(geography: Geography) -> MetricEvidence | None:
    source = geography.geometry_source
    if source is None:
        return None
    return MetricEvidence(
        dataset=source.dataset,
        dataset_year=source.dataset_year,
        source_variable=None,
        source_url=source.source_url,
        organization=source.organization,
    )


def build_feature(session: Session, geography: Geography) -> Feature | None:
    """Build one Feature, or ``None`` if the stored geometry is unusable.

    Returning ``None`` rather than raising keeps one corrupt boundary from
    taking down the whole map.
    """
    if not geography.geometry_geojson:
        return None
    try:
        geometry = json.loads(geography.geometry_geojson)
    except (TypeError, ValueError):
        return None
    if not isinstance(geometry, dict) or "type" not in geometry:
        return None
    coordinates = geometry.get("coordinates")
    # An empty coordinate list is structurally valid JSON but cannot be
    # drawn, and Leaflet renders it as an invisible layer that still
    # answers clicks. Treat it as no boundary at all.
    if not isinstance(coordinates, list) or not coordinates:
        return None

    metrics = {
        metric.metric_key: MetricValue(
            value=metric.value, unit=metric.unit, evidence=_evidence(metric)
        )
        for metric in CommunityMetricRepository(session).list_for_geography(
            geography.id
        )
    }

    return Feature(
        id=geography.geoid,
        geometry=Geometry(
            type=geometry["type"], coordinates=geometry["coordinates"]
        ),
        properties=FeatureProperties(
            geoid=geography.geoid,
            name=geography.name,
            geography_type=geography.geography_type,
            state_fips=geography.state_fips,
            county_fips=geography.county_fips,
            tract_code=geography.tract_code,
            boundary_source=_boundary_evidence(geography),
            metrics=metrics,
        ),
    )


def build_business_features(session: Session) -> FeatureCollection:
    """Businesses as GeoJSON Points.

    A separate collection from the area polygons: the two layers are drawn
    differently, and RFC 7946 position order is ``[longitude, latitude]`` -
    the reverse of Leaflet's own ``[lat, lng]``, which is a classic source of
    markers landing in the wrong hemisphere.
    """
    features = [
        Feature(
            id=business.external_id,
            geometry=Geometry(
                type="Point", coordinates=[business.longitude, business.latitude]
            ),
            properties=FeatureProperties(
                geoid=business.external_id,
                name=business.name,
                geography_type="business",
                boundary_source=None,
                metrics={},
                business=BusinessFeatureInfo(
                    id=business.id,
                    category=business.category,
                    address=business.address,
                    source=business.source,
                    source_url=business.source_url,
                    source_tag=business.source_tag,
                ),
            ),
        )
        for business in BusinessRepository(session).search()
    ]
    return FeatureCollection(features=features)


def build_community_map(session: Session) -> CommunityMapResponse:
    """Both map layers in one payload."""
    areas = build_feature_collection(session)
    businesses = build_business_features(session)
    return CommunityMapResponse(
        areas=areas,
        businesses=businesses,
        area_count=len(areas.features),
        business_count=len(businesses.features),
    )


def build_feature_collection(session: Session) -> FeatureCollection:
    """Every geography that has a boundary, with its metrics attached.

    Features are joined to metrics by database id, which derives from the
    GEOID - never by name.
    """
    features = [
        feature
        for geography in GeographyRepository(session).list_with_geometry()
        if (feature := build_feature(session, geography)) is not None
    ]
    return FeatureCollection(features=features)
