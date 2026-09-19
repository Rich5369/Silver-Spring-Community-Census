"""Tests for the persistence layer.

The emphasis is on the guarantees the schema is supposed to enforce rather
than on SQLAlchemy round-tripping: that a fact cannot be stored without its
evidence, that re-running ingestion updates instead of duplicating, and that
the evidence survives a round trip to disk.
"""

from __future__ import annotations

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Business, CommunityMetric, DataSource, Geography
from app.repositories import (
    BusinessRepository,
    CommunityMetricRepository,
    DataSourceRepository,
    GeographyRepository,
)
from tests.sample_data import seed


# --- Schema -----------------------------------------------------------------


def test_all_tables_created(db_engine) -> None:
    """Initialisation creates every table the models declare."""
    tables = set(inspect(db_engine).get_table_names())
    assert tables == {"data_sources", "geographies", "community_metrics", "businesses"}


def test_sqlite_enforces_foreign_keys(db_session: Session) -> None:
    """The PRAGMA listener is active.

    Without it SQLite accepts orphaned rows silently, which would make every
    foreign key in the model inert and void the evidence guarantee.
    """
    _, geography, _, _ = seed(db_session)

    db_session.add(
        CommunityMetric(
            geography_id=geography.id,
            data_source_id=99999,  # no such source
            metric_key="orphan",
            value=1.0,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


# --- The evidence guarantee -------------------------------------------------


def test_metric_cannot_be_stored_without_a_source(db_session: Session) -> None:
    """A metric with no data source violates NOT NULL. This is the core rule."""
    _, geography, _, _ = seed(db_session)

    db_session.add(
        CommunityMetric(
            geography_id=geography.id,
            data_source_id=None,
            metric_key="unsourced_population",
            value=1.0,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_business_cannot_be_stored_without_a_source(db_session: Session) -> None:
    """Nothing reaches the map without attribution either."""
    seed(db_session)

    db_session.add(
        Business(
            data_source_id=None,
            external_id="unsourced/1",
            name="Unsourced Place",
            category="Cafe",
            latitude=38.99,
            longitude=-77.02,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_metric_carries_full_evidence_after_reload(db_session: Session) -> None:
    """Dataset, year, geography, variable and URL all survive a round trip.

    This is the requirement stated end to end: every metric shown to a user
    must be traceable to the dataset it came from.
    """
    _, _, metric, _ = seed(db_session)
    metric_id = metric.id
    db_session.expunge_all()

    reloaded = db_session.get(CommunityMetric, metric_id)
    assert reloaded is not None

    assert reloaded.dataset == "TEST Sample Dataset"
    assert reloaded.dataset_year == 2023
    assert reloaded.source_url == "https://example.invalid/test-dataset"
    assert reloaded.source_variable == "TEST_VAR_001E"
    assert reloaded.unit == "people"
    assert reloaded.data_source.organization == "TEST Organization"
    assert reloaded.geography.name == "TEST Sample Tract"
    assert reloaded.geography.geoid == "TEST-0001"


def test_business_exposes_readable_attribution(db_session: Session) -> None:
    """A map popup can cite the record without extra queries."""
    _, _, _, business = seed(db_session)

    assert business.source == "TEST Organization (test/1)"
    assert business.source_url == "https://example.invalid/test-dataset"


def test_source_cannot_be_deleted_while_cited(db_session: Session) -> None:
    """``ondelete=RESTRICT`` stops evidence being removed out from under a fact."""
    source, _, _, _ = seed(db_session)

    db_session.delete(source)
    with pytest.raises(IntegrityError):
        db_session.commit()


# --- Duplicate prevention ---------------------------------------------------


def test_reingesting_a_metric_updates_in_place(db_session: Session) -> None:
    """Re-running ingestion refreshes the value instead of duplicating it."""
    source, geography, metric, _ = seed(db_session)
    repo = CommunityMetricRepository(db_session)

    updated = repo.upsert(
        geography_id=geography.id,
        data_source_id=source.id,
        metric_key="total_population",
        value=5678.0,
        unit="people",
        source_variable="TEST_VAR_001E",
    )
    db_session.commit()

    assert updated.id == metric.id
    assert updated.value == 5678.0
    assert repo.count() == 1


def test_duplicate_metric_row_is_rejected(db_session: Session) -> None:
    """The constraint holds even if something bypasses the repository."""
    source, geography, _, _ = seed(db_session)

    db_session.add(
        CommunityMetric(
            geography_id=geography.id,
            data_source_id=source.id,
            metric_key="total_population",  # same triple as the seeded row
            value=999.0,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_same_metric_from_a_different_year_is_allowed(db_session: Session) -> None:
    """A second ACS vintage is a distinct legitimate row, not a duplicate."""
    _, geography, _, _ = seed(db_session)

    other_source = DataSourceRepository(db_session).upsert(
        key="test-sample-source-2019",
        organization="TEST Organization",
        dataset="TEST Sample Dataset",
        dataset_year=2019,
        source_url="https://example.invalid/test-dataset-2019",
    )
    CommunityMetricRepository(db_session).upsert(
        geography_id=geography.id,
        data_source_id=other_source.id,
        metric_key="total_population",
        value=1000.0,
        unit="people",
    )
    db_session.commit()

    assert CommunityMetricRepository(db_session).count() == 2


def test_reingesting_a_business_updates_in_place(db_session: Session) -> None:
    """Same source plus same external id means the same place."""
    source, _, _, business = seed(db_session)
    repo = BusinessRepository(db_session)

    updated = repo.upsert(
        data_source_id=source.id,
        external_id="test/1",
        name="TEST Sample Cafe (renamed)",
        category="Cafe",
        latitude=38.9921,
        longitude=-77.0242,
    )
    db_session.commit()

    assert updated.id == business.id
    assert updated.name == "TEST Sample Cafe (renamed)"
    assert repo.count() == 1


def test_geography_upsert_is_keyed_on_geoid(db_session: Session) -> None:
    """Re-ingesting a tract updates its name rather than adding a row."""
    _, geography, _, _ = seed(db_session)
    repo = GeographyRepository(db_session)

    updated = repo.upsert(
        geoid="TEST-0001", name="TEST Renamed Tract", geography_type="tract"
    )
    db_session.commit()

    assert updated.id == geography.id
    assert repo.count() == 1


def test_geography_upsert_preserves_existing_geometry(db_session: Session) -> None:
    """A metadata-only refresh must not wipe a boundary already loaded."""
    seed(db_session)
    repo = GeographyRepository(db_session)

    updated = repo.upsert(
        geoid="TEST-0001", name="TEST Renamed Tract", geography_type="tract"
    )
    db_session.commit()

    assert updated.geometry_geojson == '{"type": "Polygon", "coordinates": []}'


def test_duplicate_data_source_key_is_rejected(db_session: Session) -> None:
    """Dataset slugs are unique, so citations cannot fork."""
    seed(db_session)

    db_session.add(
        DataSource(
            key="test-sample-source",
            organization="Other",
            dataset="Other",
            source_url="https://example.invalid/other",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


# --- Coordinate validation --------------------------------------------------


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [(91.0, -77.0), (-91.0, -77.0), (38.9, 181.0), (38.9, -181.0)],
)
def test_out_of_range_coordinates_are_rejected(
    db_session: Session, latitude: float, longitude: float
) -> None:
    """Transposed or malformed coordinates are caught at write time.

    Otherwise they surface as markers in the middle of the ocean during a
    demo, which is a slow and embarrassing way to find the bug.
    """
    source, _, _, _ = seed(db_session)

    db_session.add(
        Business(
            data_source_id=source.id,
            external_id="test/bad-coords",
            name="TEST Bad Coordinates",
            category="Cafe",
            latitude=latitude,
            longitude=longitude,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


# --- Query layer ------------------------------------------------------------


def test_business_search_filters_by_category_and_name(db_session: Session) -> None:
    """The query the /businesses route will delegate to."""
    source, _, _, _ = seed(db_session)
    repo = BusinessRepository(db_session)
    repo.upsert(
        data_source_id=source.id,
        external_id="test/2",
        name="TEST Sample Bakery",
        category="Bakery",
        latitude=38.993,
        longitude=-77.026,
    )
    db_session.commit()

    assert len(repo.search()) == 2
    assert [b.name for b in repo.search(category="Bakery")] == ["TEST Sample Bakery"]
    assert [b.name for b in repo.search(query="cafe")] == ["TEST Sample Cafe"]
    assert repo.search(category="Bakery", query="cafe") == []


def test_business_search_escapes_like_wildcards(db_session: Session) -> None:
    """A user-supplied '%' must not match every record."""
    seed(db_session)

    assert BusinessRepository(db_session).search(query="%") == []


def test_list_metrics_for_geography(db_session: Session) -> None:
    """Profile assembly reads every metric for an area in one call."""
    _, geography, _, _ = seed(db_session)

    metrics = CommunityMetricRepository(db_session).list_for_geography(geography.id)

    assert [m.metric_key for m in metrics] == ["total_population"]
    # Evidence is eagerly loaded, so no caller can serve a value unattributed.
    assert metrics[0].data_source.dataset == "TEST Sample Dataset"


def test_suppressed_metric_value_is_stored_as_null(db_session: Session) -> None:
    """The Census suppresses small-population estimates.

    A missing value must stay missing rather than being coerced to zero,
    which would read as a real measurement of nobody living there.
    """
    source, geography, _, _ = seed(db_session)

    metric = CommunityMetricRepository(db_session).upsert(
        geography_id=geography.id,
        data_source_id=source.id,
        metric_key="median_household_income",
        value=None,
        unit="usd",
        source_variable="TEST_VAR_002E",
    )
    db_session.commit()

    assert metric.value is None


# --- Isolation --------------------------------------------------------------


def test_database_is_isolated_per_test(db_session: Session) -> None:
    """Each test gets an empty database, so ordering cannot mask a bug."""
    assert DataSourceRepository(db_session).count() == 0
    assert GeographyRepository(db_session).count() == 0
    assert CommunityMetricRepository(db_session).count() == 0
    assert BusinessRepository(db_session).count() == 0
