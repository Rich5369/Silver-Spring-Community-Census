"""Tests for the Census integration.

No test in this module touches the network: every response is served by an
``httpx.MockTransport``. That keeps the suite fast, offline and independent
of Census rate limits.
"""

from __future__ import annotations

import httpx
import pytest
from sqlalchemy.orm import Session

from app.integrations.census.client import (
    CensusApiError,
    CensusClient,
    GeographyQuery,
    redact,
)
from app.integrations.census.targets import (
    MONTGOMERY_COUNTY,
    MONTGOMERY_COUNTY_TRACTS,
)
from app.integrations.census.transform import (
    compute_metrics,
    parse_geography,
    parse_value,
)
from app.integrations.census.variables import (
    ACS_VARIABLES,
    METRIC_SPECS,
    METRIC_SPECS_BY_KEY,
    required_variable_ids,
)
from app.models import CommunityMetric
from app.repositories import CommunityMetricRepository, GeographyRepository
from app.services.census_ingest_service import ingest_geography

COUNTY_QUERY = GeographyQuery(for_clause="county:031", in_clause="state:24")

# A realistic county row. Values are plausible but fabricated for testing.
SAMPLE_VALUES: dict[str, str] = {
    "B01003_001E": "1057586",
    "B01002_001E": "39.4",
    "B19013_001E": "129000",
    "B01001_001E": "1057586",
    "B01001_007E": "5000",
    "B01001_008E": "6000",
    "B01001_009E": "6000",
    "B01001_010E": "18000",
    "B01001_011E": "35000",
    "B01001_012E": "38000",
    "B01001_031E": "5000",
    "B01001_032E": "6000",
    "B01001_033E": "6000",
    "B01001_034E": "18000",
    "B01001_035E": "36000",
    "B01001_036E": "39000",
    "B25003_001E": "383000",
    "B25003_002E": "250000",
    "B25003_003E": "133000",
    "B08301_001E": "520000",
    "B08301_003E": "300000",
    "B08301_004E": "40000",
    "B08301_010E": "50000",
    "B08301_018E": "2000",
    "B08301_019E": "18000",
    "B08301_021E": "110000",
    "B15003_001E": "740000",
    "B15003_022E": "200000",
    "B15003_023E": "150000",
    "B15003_024E": "30000",
    "B15003_025E": "25000",
    "C16002_001E": "383000",
    "C16002_002E": "230000",
}

GEO_COLUMNS = {"state": "24", "county": "031"}


def _matrix(values: dict[str, str], geo: dict[str, str], name: str) -> list[list[str]]:
    """Build a Census-shaped matrix: a header row then data rows."""
    variables = list(values)
    header = ["NAME", *variables, *geo]
    row = [name, *[values[v] for v in variables], *geo.values()]
    return [header, row]


def _client(handler) -> CensusClient:
    return CensusClient(
        year=2024,
        dataset="acs/acs5",
        api_key="TEST-KEY-NOT-REAL",
        transport=httpx.MockTransport(handler),
    )


def _ok_handler(request: httpx.Request) -> httpx.Response:
    """Return only the variables the request asked for, as the API does."""
    requested = request.url.params.get("get", "").split(",")
    values = {v: SAMPLE_VALUES[v] for v in requested if v in SAMPLE_VALUES}
    return httpx.Response(
        200, json=_matrix(values, GEO_COLUMNS, "Montgomery County, Maryland")
    )


# --- Variable catalogue -----------------------------------------------------


def test_every_metric_input_is_catalogued() -> None:
    """No metric may reference a variable we have no documented label for."""
    for spec in METRIC_SPECS:
        for variable_id in spec.all_variable_ids:
            assert variable_id in ACS_VARIABLES, f"{spec.metric_key} -> {variable_id}"


def test_catalogued_variables_have_labels_and_descriptions() -> None:
    """Provenance is only useful if a human can read it."""
    for variable in ACS_VARIABLES.values():
        assert variable.label.strip()
        assert variable.description.strip()
        assert variable.group == variable.variable_id.split("_", 1)[0]


def test_metric_keys_are_unique() -> None:
    assert len(METRIC_SPECS_BY_KEY) == len(METRIC_SPECS)


def test_required_variables_are_deduplicated() -> None:
    """Shared table bases must not be requested twice."""
    ids = required_variable_ids()
    assert len(ids) == len(set(ids))


def test_variable_count_is_within_api_limits() -> None:
    """A single uncached request must stay usable against the API's cap."""
    assert len(required_variable_ids()) <= 50


def test_source_variable_formula_is_reproducible() -> None:
    """A derived metric records the arithmetic behind it, not just a table."""
    assert METRIC_SPECS_BY_KEY["total_population"].source_variable == "B01003_001E"
    assert (
        METRIC_SPECS_BY_KEY["multilingual_households"].source_variable
        == "C16002_001E - C16002_002E"
    )
    share = METRIC_SPECS_BY_KEY["renter_share"].source_variable
    assert share == "(B25003_003E) / B25003_001E * 100"


# --- Value parsing ----------------------------------------------------------


@pytest.mark.parametrize(
    "raw",
    ["-666666666", "-999999999", "-888888888", "-222222222", "-555555555"],
)
def test_census_null_sentinels_become_none(raw: str) -> None:
    """Sentinels must never reach the user as '-666666666 residents'."""
    assert parse_value(raw) is None


@pytest.mark.parametrize("raw", [None, "", "   ", "null", "N/A", "not-a-number", "*"])
def test_malformed_values_become_none(raw: str | None) -> None:
    assert parse_value(raw) is None


@pytest.mark.parametrize(
    ("raw", "expected"), [("0", 0.0), ("1057586", 1057586.0), ("39.4", 39.4)]
)
def test_valid_values_parse(raw: str, expected: float) -> None:
    assert parse_value(raw) == expected


def test_zero_is_preserved_not_treated_as_missing() -> None:
    """Zero bicycle commuters is a measurement, not an absence of one."""
    assert parse_value("0") == 0.0


# --- Metric computation -----------------------------------------------------


def _metrics(values: dict[str, str]) -> dict[str, float | None]:
    return {m.metric_key: m.value for m in compute_metrics(values)}


def test_direct_sum_and_share_metrics() -> None:
    metrics = _metrics(SAMPLE_VALUES)

    assert metrics["total_population"] == 1057586.0
    assert metrics["median_household_income"] == 129000.0
    # male 18-19..30-34 = 5000+6000+6000+18000+35000+38000
    # female 18-19..30-34 = 5000+6000+6000+18000+36000+39000
    assert metrics["young_adults_18_34"] == 218000.0
    assert metrics["renter_occupied_households"] == 133000.0
    assert metrics["renter_share"] == round(133000 / 383000 * 100, 2)
    # public transport + bicycle + walked, over all workers
    assert metrics["commute_active_share"] == round(70000 / 520000 * 100, 2)
    assert metrics["bachelors_or_higher"] == 405000.0


def test_difference_metric_subtracts_english_only_households() -> None:
    metrics = _metrics(SAMPLE_VALUES)

    assert metrics["multilingual_households"] == 153000.0
    assert metrics["multilingual_household_share"] == round(153000 / 383000 * 100, 2)


def test_suppressed_input_yields_missing_metric_not_zero() -> None:
    """A suppressed median must be reported as unavailable."""
    values = {**SAMPLE_VALUES, "B19013_001E": "-666666666"}

    assert _metrics(values)["median_household_income"] is None


def test_partial_sum_is_reported_as_missing() -> None:
    """A sum missing a component is wrong, so it is not reported at all."""
    values = {**SAMPLE_VALUES, "B01001_011E": "-666666666"}
    metrics = _metrics(values)

    assert metrics["young_adults_18_34"] is None
    assert metrics["young_adult_share"] is None


def test_zero_denominator_yields_none_not_division_error() -> None:
    """A tract with no workers has no commute share - undefined, not zero."""
    values = {**SAMPLE_VALUES, "B08301_001E": "0"}

    assert _metrics(values)["commute_active_share"] is None


def test_every_metric_is_computed_for_a_complete_row() -> None:
    metrics = _metrics(SAMPLE_VALUES)

    assert len(metrics) == len(METRIC_SPECS)
    assert all(value is not None for value in metrics.values())


# --- Geography parsing ------------------------------------------------------


def test_county_geoid_is_state_plus_county() -> None:
    geography = parse_geography(
        {"NAME": "Montgomery County, Maryland", "state": "24", "county": "031"}
    )

    assert geography.geoid == "24031"
    assert geography.geography_type == "county"
    assert geography.tract_code is None


def test_tract_geoid_concatenates_the_hierarchy() -> None:
    geography = parse_geography(
        {
            "NAME": "Census Tract 7017, Montgomery County, Maryland",
            "state": "24",
            "county": "031",
            "tract": "701700",
        }
    )

    assert geography.geoid == "24031701700"
    assert geography.geography_type == "tract"
    assert geography.tract_code == "701700"


def test_targets_point_at_montgomery_county() -> None:
    """Guard against a typo silently ingesting the wrong county."""
    assert MONTGOMERY_COUNTY.for_clause == "county:031"
    assert MONTGOMERY_COUNTY.in_clause == "state:24"
    assert MONTGOMERY_COUNTY_TRACTS.for_clause == "tract:*"
    assert MONTGOMERY_COUNTY_TRACTS.in_clause == "state:24 county:031"


# --- Client -----------------------------------------------------------------


def test_fetch_returns_row_dicts() -> None:
    rows = _client(_ok_handler).fetch(["B01003_001E"], COUNTY_QUERY)

    assert len(rows) == 1
    assert rows[0]["B01003_001E"] == "1057586"
    assert rows[0]["state"] == "24"


def test_fetch_sends_key_and_geography_parameters() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(dict(request.url.params))
        return _ok_handler(request)

    _client(handler).fetch(["B01003_001E"], COUNTY_QUERY)

    assert seen["key"] == "TEST-KEY-NOT-REAL"
    assert seen["for"] == "county:031"
    assert seen["in"] == "state:24"
    assert seen["get"].startswith("NAME,")


def test_client_works_without_an_api_key() -> None:
    """The API allows 500 requests/day unkeyed, so ingestion must not require one."""
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(dict(request.url.params))
        return _ok_handler(request)

    client = CensusClient(
        year=2024, dataset="acs/acs5", api_key=None,
        transport=httpx.MockTransport(handler),
    )
    client.fetch(["B01003_001E"], COUNTY_QUERY)

    assert "key" not in seen


def test_large_variable_sets_are_chunked_and_merged() -> None:
    """All 31 variables arrive on one row despite the per-request cap."""
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested = request.url.params.get("get", "").split(",")
        calls.append(len(requested))
        return _ok_handler(request)

    rows = _client(handler).fetch(list(SAMPLE_VALUES), COUNTY_QUERY)

    assert len(calls) == 1 if len(SAMPLE_VALUES) <= 45 else len(calls) > 1
    assert len(rows) == 1
    assert set(SAMPLE_VALUES).issubset(rows[0])


def test_chunking_merges_multiple_requests_onto_one_row() -> None:
    """Force chunking with a small cap to prove the merge, not just the path."""
    from app.integrations.census import client as client_module

    original = client_module.MAX_VARIABLES_PER_REQUEST
    client_module.MAX_VARIABLES_PER_REQUEST = 5
    try:
        calls: list[int] = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(1)
            return _ok_handler(request)

        rows = _client(handler).fetch(list(SAMPLE_VALUES), COUNTY_QUERY)
    finally:
        client_module.MAX_VARIABLES_PER_REQUEST = original

    assert len(calls) > 1
    assert len(rows) == 1
    assert set(SAMPLE_VALUES).issubset(rows[0])


@pytest.mark.parametrize("status", [400, 401, 403, 404, 429, 500, 503])
def test_non_200_responses_raise(status: int) -> None:
    client = _client(lambda request: httpx.Response(status, text="upstream error"))

    with pytest.raises(CensusApiError, match=str(status)):
        client.fetch(["B01003_001E"], COUNTY_QUERY)


def test_non_json_response_raises() -> None:
    client = _client(lambda request: httpx.Response(200, text="<html>nope</html>"))

    with pytest.raises(CensusApiError, match="non-JSON"):
        client.fetch(["B01003_001E"], COUNTY_QUERY)


def test_unexpected_payload_shape_raises() -> None:
    client = _client(lambda request: httpx.Response(200, json={"error": "nope"}))

    with pytest.raises(CensusApiError, match="unexpected payload"):
        client.fetch(["B01003_001E"], COUNTY_QUERY)


def test_timeout_raises_census_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("too slow", request=request)

    with pytest.raises(CensusApiError, match="timed out"):
        _client(handler).fetch(["B01003_001E"], COUNTY_QUERY)


def test_short_rows_are_skipped_not_misaligned() -> None:
    """A truncated row must not shift values into the wrong columns."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[
                ["NAME", "B01003_001E", "state", "county"],
                ["Truncated row", "123"],
                ["Montgomery County, Maryland", "1057586", "24", "031"],
            ],
        )

    rows = _client(handler).fetch(["B01003_001E"], COUNTY_QUERY)

    assert len(rows) == 1
    assert rows[0]["B01003_001E"] == "1057586"


def test_empty_variable_list_is_rejected() -> None:
    with pytest.raises(ValueError):
        _client(_ok_handler).fetch([], COUNTY_QUERY)


# --- Key safety -------------------------------------------------------------


def test_redact_removes_the_key() -> None:
    url = "https://api.census.gov/data/2024/acs/acs5?get=NAME&key=SECRET123&for=us:1"
    redacted = redact(url)

    assert "SECRET123" not in redacted
    assert "key=REDACTED" in redacted
    assert "for=us:1" in redacted


@pytest.mark.parametrize(
    "handler",
    [
        lambda request: httpx.Response(500, text="boom"),
        lambda request: httpx.Response(200, text="<html>"),
        lambda request: httpx.Response(200, json={"bad": "shape"}),
    ],
)
def test_error_messages_never_contain_the_api_key(handler) -> None:
    """The reason raise_for_status() is not used: it embeds the key.

    An API key in an exception message ends up in logs and tracebacks, which
    is one of the most common ways credentials leak.
    """
    client = _client(handler)

    with pytest.raises(CensusApiError) as exc_info:
        client.fetch(["B01003_001E"], COUNTY_QUERY)

    assert "TEST-KEY-NOT-REAL" not in str(exc_info.value)


def test_base_url_is_credential_free() -> None:
    """base_url is stored as the public source link, so it must be clean."""
    client = _client(_ok_handler)

    assert "key" not in client.base_url
    assert client.base_url == "https://api.census.gov/data/2024/acs/acs5"


# --- Ingestion --------------------------------------------------------------


def test_ingestion_stores_geography_metrics_and_evidence(db_session: Session) -> None:
    report = ingest_geography(db_session, _client(_ok_handler), COUNTY_QUERY)
    db_session.commit()

    assert report.geographies == 1
    assert report.metrics_written == len(METRIC_SPECS)

    geography = GeographyRepository(db_session).get_by_geoid("24031")
    assert geography is not None
    assert geography.name == "Montgomery County, Maryland"
    assert geography.state_fips == "24"

    metrics = CommunityMetricRepository(db_session).list_for_geography(geography.id)
    assert len(metrics) == len(METRIC_SPECS)

    population = next(m for m in metrics if m.metric_key == "total_population")
    assert population.value == 1057586.0
    assert population.unit == "people"
    # The full evidence chain, as required.
    assert population.source_variable == "B01003_001E"
    assert population.dataset_year == 2024
    assert population.dataset.startswith("American Community Survey 5-Year")
    assert population.source_url == "https://api.census.gov/data/2024/acs/acs5"
    assert population.data_source.organization == "US Census Bureau"
    assert population.geography.geoid == "24031"


def test_ingestion_is_idempotent(db_session: Session) -> None:
    """Re-running refreshes values instead of duplicating rows."""
    client = _client(_ok_handler)

    ingest_geography(db_session, client, COUNTY_QUERY)
    db_session.commit()
    first = CommunityMetricRepository(db_session).count()

    ingest_geography(db_session, client, COUNTY_QUERY)
    db_session.commit()

    assert CommunityMetricRepository(db_session).count() == first
    assert GeographyRepository(db_session).count() == 1


def test_reingestion_updates_changed_values(db_session: Session) -> None:
    """A new ACS vintage of the same release overwrites in place."""
    ingest_geography(db_session, _client(_ok_handler), COUNTY_QUERY)
    db_session.commit()

    def updated_handler(request: httpx.Request) -> httpx.Response:
        requested = request.url.params.get("get", "").split(",")
        values = {v: SAMPLE_VALUES[v] for v in requested if v in SAMPLE_VALUES}
        if "B01003_001E" in values:
            values["B01003_001E"] = "1100000"
        return httpx.Response(
            200, json=_matrix(values, GEO_COLUMNS, "Montgomery County, Maryland")
        )

    ingest_geography(db_session, _client(updated_handler), COUNTY_QUERY)
    db_session.commit()

    geography = GeographyRepository(db_session).get_by_geoid("24031")
    assert geography is not None
    metric = (
        db_session.query(CommunityMetric)
        .filter_by(geography_id=geography.id, metric_key="total_population")
        .one()
    )
    assert metric.value == 1100000.0


def test_suppressed_metrics_are_stored_as_null(db_session: Session) -> None:
    """Stored as NULL, not skipped, so a profile can say 'not available'."""

    def handler(request: httpx.Request) -> httpx.Response:
        requested = request.url.params.get("get", "").split(",")
        values = {v: SAMPLE_VALUES[v] for v in requested if v in SAMPLE_VALUES}
        if "B19013_001E" in values:
            values["B19013_001E"] = "-666666666"
        return httpx.Response(
            200, json=_matrix(values, GEO_COLUMNS, "Montgomery County, Maryland")
        )

    report = ingest_geography(db_session, _client(handler), COUNTY_QUERY)
    db_session.commit()

    assert report.metrics_missing >= 1
    geography = GeographyRepository(db_session).get_by_geoid("24031")
    assert geography is not None
    metric = (
        db_session.query(CommunityMetric)
        .filter_by(geography_id=geography.id, metric_key="median_household_income")
        .one()
    )
    assert metric.value is None
    # Evidence is recorded even when the value is unavailable.
    assert metric.source_variable == "B19013_001E"


def test_ingestion_failure_does_not_write_partial_data(db_session: Session) -> None:
    """A failed fetch leaves the database untouched."""
    client = _client(lambda request: httpx.Response(503, text="unavailable"))

    with pytest.raises(CensusApiError):
        ingest_geography(db_session, client, COUNTY_QUERY)
    db_session.rollback()

    assert CommunityMetricRepository(db_session).count() == 0
    assert GeographyRepository(db_session).count() == 0
