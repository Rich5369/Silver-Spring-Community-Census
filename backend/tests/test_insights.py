"""Tests for deterministic insights.

The calculations are checked against values computed by hand in the test, not
against whatever the implementation happens to produce.
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.repositories import (
    BusinessRepository,
    CommunityMetricRepository,
    DataSourceRepository,
    GeographyRepository,
)
from app.services.insights_service import build_insights

ENDPOINT = "/api/v1/insights/fenton-village"

POLYGON = (
    '{"type": "Polygon", "coordinates": '
    "[[[-77.03, 38.99], [-77.02, 38.99], [-77.02, 39.0], [-77.03, 38.99]]]}"
)

# Two tracts with deliberately different sizes, so a size-weighted share can
# be told apart from a naive average of per-tract shares.
TRACT_A = {
    "total_population": 1000.0,
    "young_adults_18_34": 300.0,
    "occupied_housing_units": 400.0,
    "renter_occupied_households": 300.0,
    "owner_occupied_households": 100.0,
    "commuters_total": 500.0,
    "commute_public_transport": 100.0,
    "commute_walked": 40.0,
    "commute_bicycle": 10.0,
    "worked_from_home": 50.0,
    "multilingual_households": 200.0,
    "bachelors_or_higher": 600.0,
    "median_household_income": 80000.0,
    "median_age": 33.0,
}
TRACT_B = {
    "total_population": 3000.0,
    "young_adults_18_34": 300.0,
    "occupied_housing_units": 1600.0,
    "renter_occupied_households": 400.0,
    "owner_occupied_households": 1200.0,
    "commuters_total": 1500.0,
    "commute_public_transport": 200.0,
    "commute_walked": 50.0,
    "commute_bicycle": 0.0,
    "worked_from_home": 250.0,
    "multilingual_households": 200.0,
    "bachelors_or_higher": 1200.0,
    "median_household_income": 140000.0,
    "median_age": 45.0,
}

UNITS = {"median_household_income": "usd", "median_age": "years"}


def _seed_area(session: Session, tracts: dict[str, dict[str, float]]) -> None:
    """Create tracts with boundaries and metrics."""
    source = DataSourceRepository(session).upsert(
        key="acs5-2024",
        organization="US Census Bureau",
        dataset="American Community Survey 5-Year Estimates (2024)",
        dataset_year=2024,
        source_url="https://api.census.gov/data/2024/acs/acs5",
    )
    geo_repo = GeographyRepository(session)
    metric_repo = CommunityMetricRepository(session)

    for geoid, metrics in tracts.items():
        geography = geo_repo.upsert(
            geoid=geoid,
            name=f"Census Tract {geoid}",
            geography_type="tract",
            state_fips="24",
            county_fips="031",
            geometry_geojson=POLYGON,
        )
        for key, value in metrics.items():
            metric_repo.upsert(
                geography_id=geography.id,
                data_source_id=source.id,
                metric_key=key,
                value=value,
                unit=UNITS.get(key, "people"),
                source_variable=f"VAR_{key}",
            )
    session.commit()


def _seed_businesses(session: Session, categories: list[str]) -> None:
    source = DataSourceRepository(session).upsert(
        key="openstreetmap-overpass",
        organization="OpenStreetMap contributors",
        dataset="OpenStreetMap POIs via Overpass API",
        source_url="https://www.openstreetmap.org/copyright",
    )
    repository = BusinessRepository(session)
    for index, category in enumerate(categories):
        repository.upsert(
            data_source_id=source.id,
            external_id=f"node/{index}",
            name=f"Place {index}",
            category=category,
            latitude=38.992,
            longitude=-77.024,
        )
    session.commit()


def _full_area(session: Session) -> None:
    _seed_area(session, {"24031000100": TRACT_A, "24031000200": TRACT_B})


def _snapshot(response: dict) -> dict[str, dict]:
    return {v["key"]: v for v in response["community_snapshot"]}


# --- Aggregation ------------------------------------------------------------


def test_counts_are_summed_across_tracts(db_session: Session) -> None:
    _full_area(db_session)

    snapshot = {v.key: v for v in build_insights(db_session).community_snapshot}

    assert snapshot["total_population"].value == 4000.0  # 1000 + 3000
    assert snapshot["occupied_housing_units"].value == 2000.0  # 400 + 1600
    assert snapshot["renter_occupied_households"].value == 700.0  # 300 + 400


def test_shares_are_size_weighted_not_averaged(db_session: Session) -> None:
    """The distinction that makes the number correct.

    Tract A is 75% renters, tract B is 25%. A naive average of per-tract
    shares gives 50%. The correct size-weighted answer is 700/2000 = 35%,
    because tract B has four times the housing units.
    """
    _full_area(db_session)

    renter_share = {
        v.key: v for v in build_insights(db_session).community_snapshot
    }["renter_share"]

    assert renter_share.value == 35.0
    assert renter_share.value != 50.0, "must not be a mean of per-tract shares"


def test_share_identifies_numerator_and_denominator(db_session: Session) -> None:
    """Required: a derived percentage must name its inputs."""
    _full_area(db_session)

    share = {v.key: v for v in build_insights(db_session).community_snapshot}[
        "renter_share"
    ]

    assert share.derivation is not None
    assert share.derivation.method == "ratio"
    assert share.derivation.numerator_metrics == ["renter_occupied_households"]
    assert share.derivation.denominator_metric == "occupied_housing_units"
    assert share.derivation.numerator_value == 700.0
    assert share.derivation.denominator_value == 2000.0
    assert share.derivation.formula == (
        "sum(renter_occupied_households) / sum(occupied_housing_units) * 100"
    )


def test_multi_component_share_sums_three_modes(db_session: Session) -> None:
    """(100+40+10) + (200+50+0) = 400 over 2000 workers = 20%."""
    _full_area(db_session)

    share = {v.key: v for v in build_insights(db_session).community_snapshot}[
        "commute_active_share"
    ]

    assert share.value == 20.0
    assert share.derivation is not None
    assert share.derivation.numerator_value == 400.0
    assert share.derivation.denominator_value == 2000.0


def test_young_adult_share(db_session: Session) -> None:
    """600 of 4000 = 15%."""
    _full_area(db_session)

    share = {v.key: v for v in build_insights(db_session).community_snapshot}[
        "young_adult_share"
    ]

    assert share.value == 15.0


# --- Medians are not aggregated ---------------------------------------------


def test_medians_are_reported_as_a_range(db_session: Session) -> None:
    """A median is not additive, so only the spread is reported."""
    _full_area(db_session)

    ranges = {r.key: r for r in build_insights(db_session).ranges}
    income = ranges["median_household_income"]

    assert income.available is True
    assert income.minimum == 80000.0
    assert income.maximum == 140000.0
    assert ranges["median_age"].minimum == 33.0
    assert ranges["median_age"].maximum == 45.0


def test_district_median_is_explicitly_unavailable(db_session: Session) -> None:
    """The core honesty requirement: do not invent a statistic.

    Averaging tract medians would produce a plausible-looking number that the
    source data does not support, so it is refused with a reason instead.
    """
    _full_area(db_session)

    unavailable = {u.key: u.reason for u in build_insights(db_session).unavailable}

    assert "median_household_income_district" in unavailable
    assert "median_age_district" in unavailable
    assert "not additive" in unavailable["median_household_income_district"]

    # And no snapshot entry smuggles one in.
    keys = {v.key for v in build_insights(db_session).community_snapshot}
    assert "median_household_income" not in keys
    assert "median_age" not in keys


# --- Missing data -----------------------------------------------------------


def test_missing_metric_is_unavailable_not_zero(db_session: Session) -> None:
    """Absence must never be presented as a measurement of zero."""
    tract = {k: v for k, v in TRACT_A.items() if k != "total_population"}
    _seed_area(db_session, {"24031000100": tract})

    result = build_insights(db_session)
    snapshot = {v.key: v for v in result.community_snapshot}

    population = snapshot["total_population"]
    assert population.available is False
    assert population.value is None
    assert "total_population" in (population.unavailable_reason or "")
    assert any(u.key == "total_population" for u in result.unavailable)


def test_share_is_unavailable_when_an_input_is_missing(db_session: Session) -> None:
    tract = {k: v for k, v in TRACT_A.items() if k != "occupied_housing_units"}
    _seed_area(db_session, {"24031000100": tract})

    share = {v.key: v for v in build_insights(db_session).community_snapshot}[
        "renter_share"
    ]

    assert share.available is False
    assert share.value is None
    assert "occupied_housing_units" in (share.unavailable_reason or "")


def test_null_value_is_skipped_not_counted_as_zero(db_session: Session) -> None:
    """A suppressed tract lowers coverage; it does not drag the total down."""
    _seed_area(db_session, {"24031000100": TRACT_A})
    source = DataSourceRepository(db_session).get_by_key("acs5-2024")
    geography = GeographyRepository(db_session).get_by_geoid("24031000100")
    assert source is not None and geography is not None

    second = GeographyRepository(db_session).upsert(
        geoid="24031000200",
        name="Census Tract 2",
        geography_type="tract",
        geometry_geojson=POLYGON,
    )
    CommunityMetricRepository(db_session).upsert(
        geography_id=second.id,
        data_source_id=source.id,
        metric_key="total_population",
        value=None,
        unit="people",
    )
    db_session.commit()

    population = {
        v.key: v for v in build_insights(db_session).community_snapshot
    }["total_population"]

    assert population.value == 1000.0, "the null tract must not add 0 or reduce the sum"
    assert population.coverage is not None
    assert population.coverage.tracts_with_data == 1
    assert population.coverage.tracts_total == 2
    assert population.coverage.complete is False


def test_zero_denominator_is_undefined_not_zero(db_session: Session) -> None:
    tract = {**TRACT_A, "occupied_housing_units": 0.0}
    _seed_area(db_session, {"24031000100": tract})

    share = {v.key: v for v in build_insights(db_session).community_snapshot}[
        "renter_share"
    ]

    assert share.available is False
    assert "undefined rather than zero" in (share.unavailable_reason or "")


def test_empty_database_produces_a_valid_response(db_session: Session) -> None:
    result = build_insights(db_session)

    assert result.study_area.tract_count == 0
    assert result.business_landscape.total_businesses == 0
    assert result.observations == []


# --- Business landscape -----------------------------------------------------


def test_business_category_counts_and_shares(db_session: Session) -> None:
    _seed_businesses(db_session, ["Cafe"] * 3 + ["Restaurant"] * 5 + ["Retail"] * 2)

    landscape = build_insights(db_session).business_landscape

    assert landscape.total_businesses == 10
    assert landscape.category_count == 3
    assert landscape.categories[0].category == "Restaurant"
    assert landscape.categories[0].count == 5
    assert landscape.categories[0].share_of_total == 50.0


# --- Observations -----------------------------------------------------------


def test_largest_category_observation_matches_the_example(
    db_session: Session,
) -> None:
    """The statement style specified: factual, with counts, no advice."""
    _seed_businesses(db_session, ["Restaurant"] * 37 + ["Cafe"] * 10)

    observation = next(
        o
        for o in build_insights(db_session).observations
        if o.id == "largest_business_category"
    )

    assert observation.statement == (
        "Restaurant is the largest business category in the current dataset, "
        "with 37 of 47 mapped establishments (78.72%)."
    )
    assert observation.derivation is not None
    assert observation.derivation.numerator_value == 37.0
    assert observation.derivation.denominator_value == 47.0


def test_observations_state_no_recommendation_or_causation(
    db_session: Session,
) -> None:
    """Guard the constraint that matters most.

    Deterministic templates cannot drift on their own, but a future edit
    could, so the prohibited vocabulary is asserted directly.
    """
    _full_area(db_session)
    _seed_businesses(db_session, ["Cafe"] * 3 + ["Restaurant"] * 5)

    forbidden = (
        "should", "must", "need", "needs", "recommend", "opportunity",
        "gap", "underserved", "saturated", "consider", "suggest", "ideal",
        "because", "due to", "driven by", "caused", "leads to", "results in",
        "therefore", "demand for", "potential",
    )

    for observation in build_insights(db_session).observations:
        lowered = observation.statement.lower()
        for word in forbidden:
            assert word not in lowered, (
                f"observation {observation.id!r} contains {word!r}: "
                f"{observation.statement}"
            )


def test_every_observation_carries_evidence_and_basis(
    db_session: Session,
) -> None:
    _full_area(db_session)
    _seed_businesses(db_session, ["Cafe"] * 2)

    for observation in build_insights(db_session).observations:
        assert observation.basis_metrics, f"{observation.id} has no basis metrics"
        assert observation.evidence, f"{observation.id} has no evidence"
        for evidence in observation.evidence:
            assert evidence.dataset
            assert evidence.source_url
            assert evidence.organization


def test_observations_are_deterministic(db_session: Session) -> None:
    """Same data in, byte-identical summary out."""
    _full_area(db_session)
    _seed_businesses(db_session, ["Cafe"] * 3 + ["Restaurant"] * 5)

    first = build_insights(db_session).model_dump_json()
    second = build_insights(db_session).model_dump_json()

    assert first == second


def test_no_observations_are_produced_without_data(db_session: Session) -> None:
    """Nothing is asserted about an empty dataset."""
    assert build_insights(db_session).observations == []


# --- Endpoint ---------------------------------------------------------------


def test_endpoint_returns_the_full_structure(
    client: TestClient, db_session: Session
) -> None:
    _full_area(db_session)
    _seed_businesses(db_session, ["Cafe"] * 3 + ["Restaurant"] * 5)

    response = client.get(ENDPOINT)

    assert response.status_code == 200
    payload = response.json()
    for section in (
        "study_area",
        "community_snapshot",
        "ranges",
        "business_landscape",
        "observations",
        "unavailable",
    ):
        assert section in payload

    assert payload["study_area"]["tract_count"] == 2
    assert "not a Census geography" in payload["study_area"]["method"]


def test_endpoint_separates_observations_from_source_data(
    client: TestClient, db_session: Session
) -> None:
    """Required: factual statements are not mixed into the source values."""
    _full_area(db_session)

    payload = client.get(ENDPOINT).json()

    assert isinstance(payload["observations"], list)
    for value in payload["community_snapshot"]:
        assert "statement" not in value
    for observation in payload["observations"]:
        assert "statement" in observation


def test_endpoint_snapshot_values_all_carry_evidence_or_a_reason(
    client: TestClient, db_session: Session
) -> None:
    _full_area(db_session)

    for value in _snapshot(client.get(ENDPOINT).json()).values():
        if value["available"]:
            assert value["evidence"], f"{value['key']} has no evidence"
            assert value["derivation"] is not None
        else:
            assert value["unavailable_reason"]


def test_endpoint_on_empty_database(client: TestClient) -> None:
    response = client.get(ENDPOINT)

    assert response.status_code == 200
    assert response.json()["observations"] == []


def test_response_is_json_serialisable(db_session: Session) -> None:
    _full_area(db_session)

    json.loads(build_insights(db_session).model_dump_json())
