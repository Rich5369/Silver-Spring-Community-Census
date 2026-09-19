"""Tests for the government trends series.

Median household income is the interesting case: it is a median, so it is
reported as the range across tracts rather than a sum. These tests pin that
behaviour, because summing it would produce a plausible-looking number that
the source data does not support.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.repositories import (
    CommunityMetricRepository,
    DataSourceRepository,
    GeographyRepository,
)
from app.services.trends_service import build_government_trends

POLYGON = (
    '{"type": "Polygon", "coordinates": '
    "[[[-77.03, 38.99], [-77.02, 38.99], [-77.02, 39.0], [-77.03, 38.99]]]}"
)

# Two tracts, three releases. Incomes are far apart so a range is clearly
# distinguishable from a sum or a mean.
INCOME = {
    2022: (60000.0, 140000.0),
    2023: (65000.0, 150000.0),
    2024: (70000.0, 160000.0),
}
POPULATION = {2022: (1000.0, 2000.0), 2023: (1100.0, 2100.0), 2024: (1200.0, 2200.0)}


def _seed(session: Session) -> None:
    geographies = []
    for index in (1, 2):
        geographies.append(
            GeographyRepository(session).upsert(
                geoid=f"TEST-TRACT-{index}",
                name=f"TEST Tract {index}",
                geography_type="tract",
                state_fips="24",
                county_fips="031",
                tract_code=f"00010{index}",
                geometry_geojson=POLYGON,
            )
        )
    for year in INCOME:
        source = DataSourceRepository(session).upsert(
            key=f"test-acs5-{year}",
            organization="TEST Census Bureau",
            dataset=f"TEST ACS 5-Year Estimates ({year})",
            dataset_year=year,
            source_url=f"https://example.invalid/{year}",
            license="TEST license",
        )
        for position, geography in enumerate(geographies):
            for key, table in (
                ("median_household_income", INCOME[year][position]),
                ("total_population", POPULATION[year][position]),
            ):
                CommunityMetricRepository(session).upsert(
                    geography_id=geography.id,
                    data_source_id=source.id,
                    metric_key=key,
                    value=table,
                    unit="usd" if key == "median_household_income" else "people",
                    source_variable="TEST_VAR",
                )
    session.commit()


def _series(response, key):
    return next(item for item in response.series if item.key == key)


def test_income_is_a_range_across_tracts_not_a_sum(db_session: Session) -> None:
    _seed(db_session)
    income = _series(build_government_trends(db_session), "median_household_income")

    assert income.basis == "range"
    assert [(p.year, p.low, p.high) for p in income.points] == [
        (2022, 60000.0, 140000.0),
        (2023, 65000.0, 150000.0),
        (2024, 70000.0, 160000.0),
    ]
    # A summed median would be 200000 for 2022; a mean would be 100000.
    assert all(point.value is None for point in income.points)


def test_population_stays_a_summed_total(db_session: Session) -> None:
    _seed(db_session)
    population = _series(build_government_trends(db_session), "total_population")

    assert population.basis == "total"
    assert [(p.year, p.value) for p in population.points] == [
        (2022, 3000.0),
        (2023, 3200.0),
        (2024, 3400.0),
    ]


def test_each_series_carries_its_releases_as_evidence(db_session: Session) -> None:
    _seed(db_session)
    income = _series(build_government_trends(db_session), "median_household_income")

    assert income.source is not None
    assert income.source.years == [2022, 2023, 2024]
    assert income.source.urls == [
        "https://example.invalid/2022",
        "https://example.invalid/2023",
        "https://example.invalid/2024",
    ]
    assert income.source.table == "B19013_001E"
    assert income.source.tract_count == 2


def test_trends_endpoint_exposes_the_income_range(
    client: TestClient, db_session: Session
) -> None:
    _seed(db_session)
    payload = client.get("/api/v1/government/trends").json()

    income = next(
        item for item in payload["series"] if item["key"] == "median_household_income"
    )
    assert income["basis"] == "range"
    assert income["points"][0]["low"] == 60000.0
    assert income["points"][0]["high"] == 140000.0
    assert income["source"]["years"] == [2022, 2023, 2024]
