"""Tests for boundary ingestion and GeoJSON output.

No network: TIGERweb responses are served by ``httpx.MockTransport``.
"""

from __future__ import annotations

import json

import httpx
import pytest
from sqlalchemy.orm import Session

from app.integrations.tigerweb import (
    FENTON_VILLAGE_STUDY_AREA,
    BoundingBox,
    TigerWebClient,
    TigerWebError,
)
from app.repositories import DataSourceRepository, GeographyRepository
from app.schemas.geojson import POLYGON_TYPES, FeatureCollection
from app.services.geojson_service import build_feature_collection
from tests.sample_data import seed

SQUARE = [[[-77.03, 38.99], [-77.02, 38.99], [-77.02, 39.0], [-77.03, 39.0], [-77.03, 38.99]]]


def _feature(geoid: str, name: str = "Census Tract 7017.01") -> dict:
    return {
        "type": "Feature",
        "properties": {"GEOID": geoid, "NAME": name, "STATE": "24", "COUNTY": "031"},
        "geometry": {"type": "Polygon", "coordinates": SQUARE},
    }


def _collection(*features: dict) -> dict:
    return {"type": "FeatureCollection", "features": list(features)}


def _client(handler) -> TigerWebClient:
    return TigerWebClient(transport=httpx.MockTransport(handler))


def _store_geometry(session: Session, geoid: str) -> None:
    """Attach a boundary plus its provenance to an existing geography."""
    source = DataSourceRepository(session).upsert(
        key="tigerweb-tracts-acs2024",
        organization="US Census Bureau",
        dataset="TIGERweb Census Tracts (ACS 2024 vintage)",
        dataset_year=2024,
        source_url="https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb"
        "/tigerWMS_ACS2024/MapServer/8",
    )
    GeographyRepository(session).set_geometry(
        geoid=geoid,
        geometry_geojson=json.dumps({"type": "Polygon", "coordinates": SQUARE}),
        geometry_source_id=source.id,
    )
    session.commit()


# --- Study area -------------------------------------------------------------


def test_study_area_is_scoped_to_silver_spring() -> None:
    """Guard the scope: a widened box would pull in half of Maryland."""
    box = FENTON_VILLAGE_STUDY_AREA

    assert box.min_lon < -77.01 < box.max_lon or box.max_lon <= -77.01
    assert -77.05 < box.min_lon < -77.0
    assert 38.97 < box.min_lat < 39.0
    assert box.max_lat - box.min_lat < 0.05
    assert box.max_lon - box.min_lon < 0.05


def test_envelope_serialises_in_esri_order() -> None:
    box = BoundingBox(-77.04, 38.98, -77.01, 39.005)

    assert box.as_esri_envelope() == "-77.04,38.98,-77.01,39.005"


def test_client_is_pinned_to_the_acs_2024_vintage() -> None:
    """Boundaries must match the ACS release the metrics came from."""
    url = TigerWebClient().layer_url

    assert "tigerWMS_ACS2024" in url
    assert "tigerWMS_Current" not in url
    assert url.endswith("/MapServer/8")


# --- TIGERweb client --------------------------------------------------------


def test_fetch_returns_features() -> None:
    client = _client(
        lambda request: httpx.Response(200, json=_collection(_feature("24031701701")))
    )

    features = client.fetch_tracts(FENTON_VILLAGE_STUDY_AREA)

    assert len(features) == 1
    assert features[0]["properties"]["GEOID"] == "24031701701"


def test_fetch_scopes_query_to_montgomery_county() -> None:
    """A generous bbox must never pull tracts from a neighbouring county."""
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(dict(request.url.params))
        return httpx.Response(200, json=_collection(_feature("24031701701")))

    _client(handler).fetch_tracts(FENTON_VILLAGE_STUDY_AREA)

    assert seen["where"] == "STATE='24' AND COUNTY='031'"
    assert seen["spatialRel"] == "esriSpatialRelIntersects"
    assert seen["f"] == "geojson"
    assert seen["outSR"] == "4326"
    assert "GEOID" in seen["outFields"]


def test_arcgis_error_inside_a_200_response_is_detected() -> None:
    """ArcGIS reports failures with HTTP 200, so status alone is not enough."""
    client = _client(
        lambda request: httpx.Response(200, json={"error": {"message": "bad"}})
    )

    with pytest.raises(TigerWebError, match="TIGERweb error"):
        client.fetch_tracts(FENTON_VILLAGE_STUDY_AREA)


@pytest.mark.parametrize("status", [400, 404, 500, 503])
def test_non_200_raises(status: int) -> None:
    client = _client(lambda request: httpx.Response(status, text="nope"))

    with pytest.raises(TigerWebError, match=str(status)):
        client.fetch_tracts(FENTON_VILLAGE_STUDY_AREA)


def test_non_feature_collection_raises() -> None:
    client = _client(lambda request: httpx.Response(200, json={"type": "Polygon"}))

    with pytest.raises(TigerWebError, match="FeatureCollection"):
        client.fetch_tracts(FENTON_VILLAGE_STUDY_AREA)


def test_timeout_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(TigerWebError, match="timed out"):
        _client(handler).fetch_tracts(FENTON_VILLAGE_STUDY_AREA)


# --- Joining by GEOID -------------------------------------------------------


def test_geometry_is_matched_by_geoid(db_session: Session) -> None:
    _, geography, _, _ = seed(db_session)
    _store_geometry(db_session, "TEST-0001")

    refreshed = GeographyRepository(db_session).get_by_geoid("TEST-0001")
    assert refreshed is not None
    assert refreshed.id == geography.id
    assert refreshed.geometry_source is not None


def test_unknown_geoid_is_not_silently_created(db_session: Session) -> None:
    """A boundary with no metrics behind it would render as an empty shape."""
    seed(db_session)
    before = GeographyRepository(db_session).count()

    result = GeographyRepository(db_session).set_geometry(
        geoid="24031999999", geometry_geojson="{}", geometry_source_id=1
    )

    assert result is None
    assert GeographyRepository(db_session).count() == before


def test_reingesting_geometry_overwrites_in_place(db_session: Session) -> None:
    seed(db_session)
    _store_geometry(db_session, "TEST-0001")
    _store_geometry(db_session, "TEST-0001")

    assert GeographyRepository(db_session).count() == 1
    assert len(build_feature_collection(db_session).features) == 1


# --- GeoJSON output ---------------------------------------------------------


def test_feature_collection_is_valid_geojson(db_session: Session) -> None:
    """Structural validation against RFC 7946."""
    seed(db_session)
    _store_geometry(db_session, "TEST-0001")

    collection = build_feature_collection(db_session)
    payload = json.loads(collection.model_dump_json())

    assert payload["type"] == "FeatureCollection"
    assert isinstance(payload["features"], list)

    for feature in payload["features"]:
        assert feature["type"] == "Feature"
        assert feature["geometry"]["type"] in POLYGON_TYPES
        assert isinstance(feature["geometry"]["coordinates"], list)
        assert feature["geometry"]["coordinates"]

        # Positions are [longitude, latitude] in that order per RFC 7946 -
        # the reverse of Leaflet's own [lat, lng] convention, which is a
        # classic source of markers landing in the wrong hemisphere.
        for ring in feature["geometry"]["coordinates"]:
            assert len(ring) >= 4, "a linear ring needs at least four positions"
            assert ring[0] == ring[-1], "a linear ring must be closed"
            for lon, lat in ring:
                assert -180 <= lon <= 180
                assert -90 <= lat <= 90


def test_every_feature_has_a_stable_geoid(db_session: Session) -> None:
    """The frontend joins on GEOID, so it must be present and consistent."""
    seed(db_session)
    _store_geometry(db_session, "TEST-0001")

    collection = build_feature_collection(db_session)

    for feature in collection.features:
        assert feature.id
        assert feature.properties.geoid == feature.id


def test_features_carry_metrics_and_evidence(db_session: Session) -> None:
    seed(db_session)
    _store_geometry(db_session, "TEST-0001")

    feature = build_feature_collection(db_session).features[0]
    metric = feature.properties.metrics["total_population"]

    assert metric.value == 1234.0
    assert metric.unit == "people"
    assert metric.evidence.dataset == "TEST Sample Dataset"
    assert metric.evidence.dataset_year == 2023
    assert metric.evidence.source_variable == "TEST_VAR_001E"
    assert metric.evidence.source_url == "https://example.invalid/test-dataset"


def test_boundary_provenance_is_separate_from_metric_provenance(
    db_session: Session,
) -> None:
    """Geometry and estimates are different products; both must be citable."""
    seed(db_session)
    _store_geometry(db_session, "TEST-0001")

    properties = build_feature_collection(db_session).features[0].properties

    assert properties.boundary_source is not None
    assert "TIGERweb" in properties.boundary_source.dataset
    assert properties.metrics["total_population"].evidence.dataset != (
        properties.boundary_source.dataset
    )


def test_geographies_without_geometry_are_excluded(db_session: Session) -> None:
    """A tract with metrics but no boundary cannot be drawn, so it is omitted."""
    seed(db_session)

    assert build_feature_collection(db_session).features == []


def test_corrupt_geometry_is_skipped_not_fatal(db_session: Session) -> None:
    """One bad boundary must not take down the whole map."""
    _, geography, _, _ = seed(db_session)
    geography.geometry_geojson = "{not valid json"
    db_session.commit()

    assert build_feature_collection(db_session).features == []


def test_empty_database_yields_an_empty_collection(db_session: Session) -> None:
    collection = build_feature_collection(db_session)

    assert collection.type == "FeatureCollection"
    assert collection.features == []


# --- Route ------------------------------------------------------------------


def test_geographies_endpoint_returns_a_feature_collection(client) -> None:
    """The route is reachable and always shaped as valid GeoJSON."""
    response = client.get("/geographies")

    assert response.status_code == 200
    payload = response.json()
    assert payload["type"] == "FeatureCollection"
    assert isinstance(payload["features"], list)
    FeatureCollection.model_validate(payload)
