"""Synthetic fixture data for the automated test suite.

**This data is fabricated and exists only to exercise the persistence layer.**

It lives under ``tests/`` rather than in the application package so it can
never be imported by the running service, and every value is prefixed with
``TEST`` so that a row leaking into a real database would be obvious on sight.
It is not demo data and must never be served to a user. Real content comes
from ingestion of public datasets, with real provenance.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Business, CommunityMetric, DataSource, Geography
from app.repositories import (
    BusinessRepository,
    CommunityMetricRepository,
    DataSourceRepository,
    GeographyRepository,
)

TEST_SOURCE_KEY = "test-sample-source"
TEST_GEOID = "TEST-0001"


def seed(session: Session) -> tuple[DataSource, Geography, CommunityMetric, Business]:
    """Insert one row in each table, wired together, and return them.

    Deliberately tiny: enough to prove relationships, constraints and the
    evidence chain hold, small enough that a failing assertion points
    somewhere specific.
    """
    source = DataSourceRepository(session).upsert(
        key=TEST_SOURCE_KEY,
        organization="TEST Organization",
        dataset="TEST Sample Dataset",
        dataset_year=2023,
        source_url="https://example.invalid/test-dataset",
        license="TEST license",
    )

    geography = GeographyRepository(session).upsert(
        geoid=TEST_GEOID,
        name="TEST Sample Tract",
        geography_type="tract",
        state_fips="24",
        county_fips="031",
        tract_code="000100",
        geometry_geojson='{"type": "Polygon", "coordinates": []}',
    )

    metric = CommunityMetricRepository(session).upsert(
        geography_id=geography.id,
        data_source_id=source.id,
        metric_key="total_population",
        value=1234.0,
        unit="people",
        source_variable="TEST_VAR_001E",
    )

    business = BusinessRepository(session).upsert(
        data_source_id=source.id,
        external_id="test/1",
        name="TEST Sample Cafe",
        category="Cafe",
        latitude=38.9921,
        longitude=-77.0242,
        address="1 TEST Street",
        geography_id=geography.id,
    )

    session.commit()
    return source, geography, metric, business
