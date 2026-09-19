"""Tests for the /api/v1 contract.

Happy paths plus the errors a frontend developer will actually hit: unknown
GEOIDs, unknown categories, and out-of-range parameters.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.schemas.geojson import POLYGON_TYPES
from tests.sample_data import seed

V1 = "/api/v1"


# --- Areas ------------------------------------------------------------------


def test_list_areas(client: TestClient, db_session: Session) -> None:
    seed(db_session)

    payload = client.get(f"{V1}/areas").json()

    assert payload["count"] == 1
    assert payload["areas"][0]["geoid"] == "TEST-0001"
    assert payload["areas"][0]["geography_type"] == "tract"
    assert payload["areas"][0]["has_boundary"] is True


def test_list_areas_empty_is_not_an_error(client: TestClient) -> None:
    response = client.get(f"{V1}/areas")

    assert response.status_code == 200
    assert response.json() == {"count": 0, "areas": []}


def test_areas_filter_by_type(client: TestClient, db_session: Session) -> None:
    seed(db_session)

    assert client.get(f"{V1}/areas?geography_type=tract").json()["count"] == 1
    assert client.get(f"{V1}/areas?geography_type=county").json()["count"] == 0


def test_areas_filter_by_boundary(client: TestClient, db_session: Session) -> None:
    seed(db_session)

    assert client.get(f"{V1}/areas?with_boundary_only=true").json()["count"] == 1


def test_areas_limit_is_validated(client: TestClient, db_session: Session) -> None:
    seed(db_session)

    assert client.get(f"{V1}/areas?limit=1").status_code == 200
    assert client.get(f"{V1}/areas?limit=0").status_code == 422


def test_get_area_by_geoid(client: TestClient, db_session: Session) -> None:
    seed(db_session)

    payload = client.get(f"{V1}/areas/TEST-0001").json()

    assert payload["geoid"] == "TEST-0001"
    assert payload["state_fips"] == "24"


def test_unknown_geoid_is_404_with_a_useful_message(client: TestClient) -> None:
    response = client.get(f"{V1}/areas/24031999999")

    assert response.status_code == 404
    assert "24031999999" in response.json()["detail"]


# --- Area metrics -----------------------------------------------------------


def test_area_metrics_include_evidence(
    client: TestClient, db_session: Session
) -> None:
    """The core requirement: no metric is returned without its citation."""
    seed(db_session)

    payload = client.get(f"{V1}/areas/TEST-0001/metrics").json()

    assert payload["count"] == 1
    assert payload["area"]["geoid"] == "TEST-0001"

    metric = payload["metrics"][0]
    assert metric["metric_key"] == "total_population"
    assert metric["value"] == 1234.0
    assert metric["unit"] == "people"

    evidence = metric["evidence"]
    assert evidence["dataset"] == "TEST Sample Dataset"
    assert evidence["dataset_year"] == 2023
    assert evidence["source_variable"] == "TEST_VAR_001E"
    assert evidence["source_url"] == "https://example.invalid/test-dataset"
    assert evidence["organization"] == "TEST Organization"


def test_every_metric_carries_evidence(
    client: TestClient, db_session: Session
) -> None:
    seed(db_session)

    payload = client.get(f"{V1}/areas/TEST-0001/metrics").json()

    for metric in payload["metrics"]:
        assert metric["evidence"]["dataset"]
        assert metric["evidence"]["source_url"]
        assert metric["evidence"]["organization"]


def test_metrics_for_unknown_area_is_404(client: TestClient) -> None:
    """404 means 'no such area', distinct from 'area with no metrics'."""
    response = client.get(f"{V1}/areas/24031999999/metrics")

    assert response.status_code == 404


# --- Businesses -------------------------------------------------------------


def test_list_businesses(client: TestClient, db_session: Session) -> None:
    seed(db_session)

    payload = client.get(f"{V1}/businesses").json()

    assert len(payload["businesses"]) == 1
    record = payload["businesses"][0]
    assert record["name"] == "TEST Sample Cafe"
    assert record["category"] == "Cafe"
    assert record["source"] == "TEST Organization (test/1)"


def test_business_category_filter(client: TestClient, db_session: Session) -> None:
    seed(db_session)

    assert len(client.get(f"{V1}/businesses?category=Cafe").json()["businesses"]) == 1


def test_unknown_category_returns_empty_not_404(
    client: TestClient, db_session: Session
) -> None:
    """'Show me bakeries' with no bakeries is a valid empty answer."""
    seed(db_session)

    response = client.get(f"{V1}/businesses?category=Bakery")

    assert response.status_code == 200
    assert response.json()["businesses"] == []


def test_business_name_search(client: TestClient, db_session: Session) -> None:
    seed(db_session)

    assert len(client.get(f"{V1}/businesses?q=cafe").json()["businesses"]) == 1
    assert client.get(f"{V1}/businesses?q=nonexistent").json()["businesses"] == []


def test_business_limit_is_validated(client: TestClient, db_session: Session) -> None:
    seed(db_session)

    assert client.get(f"{V1}/businesses?limit=1001").status_code == 422


def test_business_categories(client: TestClient, db_session: Session) -> None:
    seed(db_session)

    payload = client.get(f"{V1}/businesses/categories").json()

    assert payload["count"] == 1
    assert payload["categories"][0] == {"category": "Cafe", "count": 1}


def test_categories_route_is_not_shadowed(client: TestClient) -> None:
    """'categories' must not be captured as a path parameter."""
    response = client.get(f"{V1}/businesses/categories")

    assert response.status_code == 200
    assert "categories" in response.json()


# --- Map --------------------------------------------------------------------


def _give_real_boundary(db_session: Session) -> None:
    """Replace the seed's empty-coordinate placeholder with a drawable polygon.

    The fixture stores ``coordinates: []`` on purpose, which the service
    correctly refuses to emit as a feature, so a map test needs real geometry.
    """
    from app.repositories import GeographyRepository

    geography = GeographyRepository(db_session).get_by_geoid("TEST-0001")
    assert geography is not None
    geography.geometry_geojson = (
        '{"type": "Polygon", "coordinates": '
        '[[[-77.03, 38.99], [-77.02, 38.99], [-77.02, 39.0], [-77.03, 38.99]]]}'
    )
    db_session.commit()


def test_seed_placeholder_geometry_is_not_drawable(
    client: TestClient, db_session: Session
) -> None:
    """An empty coordinate list yields no feature, but still a valid payload."""
    seed(db_session)

    payload = client.get(f"{V1}/map/community").json()

    assert payload["area_count"] == 0
    assert payload["business_count"] == 1
    assert payload["areas"]["type"] == "FeatureCollection"


def test_community_map_returns_both_layers(
    client: TestClient, db_session: Session
) -> None:
    seed(db_session)
    _give_real_boundary(db_session)

    payload = client.get(f"{V1}/map/community").json()

    assert payload["area_count"] == 1
    assert payload["business_count"] == 1
    assert payload["areas"]["type"] == "FeatureCollection"
    assert payload["businesses"]["type"] == "FeatureCollection"


def test_map_area_features_are_valid_polygons(
    client: TestClient, db_session: Session
) -> None:
    seed(db_session)
    _give_real_boundary(db_session)

    feature = client.get(f"{V1}/map/community").json()["areas"]["features"][0]

    assert feature["type"] == "Feature"
    assert feature["geometry"]["type"] in POLYGON_TYPES
    assert feature["id"] == feature["properties"]["geoid"] == "TEST-0001"
    assert feature["properties"]["metrics"]["total_population"]["evidence"]["dataset"]


def test_map_business_features_are_points_in_lon_lat_order(
    client: TestClient, db_session: Session
) -> None:
    """RFC 7946 orders positions [longitude, latitude].

    That is the reverse of Leaflet's [lat, lng]; swapping them puts Silver
    Spring in Antarctica.
    """
    seed(db_session)

    feature = client.get(f"{V1}/map/community").json()["businesses"]["features"][0]

    assert feature["geometry"]["type"] == "Point"
    longitude, latitude = feature["geometry"]["coordinates"]
    assert longitude == -77.0242
    assert latitude == 38.9921
    assert feature["properties"]["business"]["category"] == "Cafe"
    assert feature["properties"]["business"]["source"]


def test_empty_map_is_valid(client: TestClient) -> None:
    payload = client.get(f"{V1}/map/community").json()

    assert payload == {
        "areas": {"type": "FeatureCollection", "features": []},
        "businesses": {"type": "FeatureCollection", "features": []},
        "area_count": 0,
        "business_count": 0,
    }


# --- Contract and docs ------------------------------------------------------


def test_openapi_documents_every_v1_route(client: TestClient) -> None:
    """The schema the frontend developer reads must list the whole contract."""
    paths = client.get("/openapi.json").json()["paths"]

    for path in (
        f"{V1}/areas",
        f"{V1}/areas/{{geoid}}",
        f"{V1}/areas/{{geoid}}/metrics",
        f"{V1}/businesses",
        f"{V1}/businesses/categories",
        f"{V1}/map/community",
    ):
        assert path in paths, f"{path} missing from OpenAPI"


def test_404_responses_are_documented(client: TestClient) -> None:
    """A documented error shape is part of the contract."""
    schema = client.get("/openapi.json").json()
    responses = schema["paths"][f"{V1}/areas/{{geoid}}"]["get"]["responses"]

    assert "404" in responses


def test_legacy_unversioned_routes_still_work(
    client: TestClient, db_session: Session
) -> None:
    """The frontend's current ENDPOINTS table must keep working.

    It calls bare paths, so removing them before it migrates would break the
    live demo.
    """
    seed(db_session)

    assert client.get("/businesses").status_code == 200
    assert client.get("/geographies").status_code == 200
    assert client.get("/health").status_code == 200


def test_cors_allows_the_configured_frontend_origin(client: TestClient) -> None:
    origin = "http://localhost:5173"

    response = client.get(f"{V1}/areas", headers={"Origin": origin})

    assert response.headers["access-control-allow-origin"] == origin
