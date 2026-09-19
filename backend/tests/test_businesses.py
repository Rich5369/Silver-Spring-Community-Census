"""Tests for OpenStreetMap business ingestion.

No test here touches Overpass: every response is served by an
``httpx.MockTransport``. Overpass is shared volunteer infrastructure, and a
test suite that hammers it would be both rude and flaky.
"""

from __future__ import annotations

import json

import httpx
import pytest
from sqlalchemy.orm import Session

from app.integrations.geo import BoundingBox
from app.integrations.osm_categories import (
    BUSINESS_CATEGORIES,
    UNCATEGORIZED,
    classify,
    is_business,
)
from app.integrations.overpass import (
    FENTON_VILLAGE_BBOX,
    OverpassClient,
    OverpassError,
    build_query,
    normalize_element,
)
from app.repositories import BusinessRepository
from app.services.business_ingest_service import ingest_businesses, store_places

# The vocabulary the frontend filters on, copied from
# src/services/businessQuery.js. If these drift apart, filter chips silently
# return nothing.
FRONTEND_CATEGORIES = {
    "Restaurant",
    "Cafe",
    "Bakery",
    "Retail",
    "Grocery",
    "Florist",
    "Health Services",
    "Personal Care",
    "Pet Services",
    "Technology Services",
    "Professional Services",
    "Bike Shop",
}


def _node(osm_id: int, tags: dict[str, str], lat=38.992, lon=-77.024) -> dict:
    return {"type": "node", "id": osm_id, "lat": lat, "lon": lon, "tags": tags}


def _payload(*elements: dict) -> dict:
    return {"version": 0.6, "elements": list(elements)}


def _client(handler) -> OverpassClient:
    return OverpassClient(transport=httpx.MockTransport(handler))


def _ok(*elements: dict):
    return lambda request: httpx.Response(200, json=_payload(*elements))


# --- Taxonomy ---------------------------------------------------------------


def test_taxonomy_matches_the_frontend_vocabulary() -> None:
    """The contract that makes the filter chips work.

    The frontend compares categories by exact string equality against a
    hardcoded list, so any drift here makes a filter return zero results
    with no error to explain why.
    """
    assert BUSINESS_CATEGORIES == FRONTEND_CATEGORIES


@pytest.mark.parametrize(
    ("tags", "expected"),
    [
        ({"amenity": "restaurant"}, "Restaurant"),
        ({"amenity": "fast_food"}, "Restaurant"),
        ({"amenity": "cafe"}, "Cafe"),
        ({"shop": "bakery"}, "Bakery"),
        ({"shop": "supermarket"}, "Grocery"),
        ({"shop": "convenience"}, "Grocery"),
        ({"shop": "florist"}, "Florist"),
        ({"shop": "bicycle"}, "Bike Shop"),
        ({"amenity": "pharmacy"}, "Health Services"),
        ({"shop": "hairdresser"}, "Personal Care"),
        ({"shop": "pet"}, "Pet Services"),
        ({"amenity": "veterinary"}, "Pet Services"),
        ({"shop": "computer"}, "Technology Services"),
        ({"shop": "mobile_phone"}, "Technology Services"),
        ({"amenity": "bank"}, "Professional Services"),
        ({"office": "lawyer"}, "Professional Services"),
        ({"shop": "clothes"}, "Retail"),
        ({"shop": "books"}, "Retail"),
    ],
)
def test_tag_classification(tags: dict[str, str], expected: str) -> None:
    category, _ = classify(tags)

    assert category == expected


def test_every_emitted_category_is_in_the_taxonomy() -> None:
    """No mapping may emit a string the frontend does not know."""
    for tags in (
        {"shop": "bakery"},
        {"amenity": "cafe"},
        {"office": "lawyer"},
        {"shop": "anything_unmapped"},
        {"healthcare": "dentist"},
        {"craft": "electronics_repair"},
    ):
        category, _ = classify(tags)
        assert category in BUSINESS_CATEGORIES


def test_specific_tag_beats_generic_shop_fallback() -> None:
    """shop=bakery must be Bakery, not the catch-all Retail."""
    assert classify({"shop": "bakery"})[0] == "Bakery"


def test_classification_records_the_deciding_tag() -> None:
    """Evidence: a surprising category must be traceable to its tag."""
    _, source_tag = classify({"shop": "florist"})

    assert source_tag == "shop=florist"


@pytest.mark.parametrize("tags", [{}, {"name": "Nameless"}, {"highway": "bus_stop"}])
def test_unclassifiable_tags_do_not_raise(tags: dict[str, str]) -> None:
    """Resilience: missing or irrelevant tags yield a fallback, not an error."""
    category, source_tag = classify(tags)

    assert category == UNCATEGORIZED
    assert source_tag is None


@pytest.mark.parametrize(
    "tags",
    [
        {"amenity": "bench"},
        {"amenity": "parking"},
        {"amenity": "waste_basket"},
        {"amenity": "drinking_water"},
        {},
    ],
)
def test_non_businesses_are_rejected(tags: dict[str, str]) -> None:
    """Street furniture carries amenity too; it is not a business."""
    assert is_business(tags) is False


@pytest.mark.parametrize(
    "tags", [{"shop": "bakery"}, {"amenity": "cafe"}, {"shop": "unmapped_thing"}]
)
def test_businesses_are_accepted(tags: dict[str, str]) -> None:
    assert is_business(tags) is True


# --- Query building ---------------------------------------------------------


def test_bbox_is_scoped_to_fenton_village() -> None:
    """Guard the scope: this is an MVP, not an OSM crawler."""
    box = FENTON_VILLAGE_BBOX

    assert box.max_lon - box.min_lon < 0.02
    assert box.max_lat - box.min_lat < 0.02
    assert box.contains(lon=-77.0242, lat=38.9921), "Fenton Village must be inside"


def test_overpass_bbox_uses_south_west_north_east_order() -> None:
    """Overpass orders bounds differently from ArcGIS.

    Swapping them silently returns an empty result set rather than an error,
    so the two orderings are separate methods and both are pinned here.
    """
    box = BoundingBox(min_lon=-77.03, min_lat=38.98, max_lon=-77.01, max_lat=38.99)

    assert box.as_overpass_bbox() == "38.98,-77.03,38.99,-77.01"
    assert box.as_esri_envelope() == "-77.03,38.98,-77.01,38.99"


def test_query_requests_business_keys_and_centres() -> None:
    query = build_query(FENTON_VILLAGE_BBOX)

    assert "[out:json]" in query
    assert "out center tags;" in query
    for key in ("shop", "amenity", "craft", "healthcare", "office"):
        assert f'nwr["{key}"]' in query


# --- Element normalisation --------------------------------------------------


def test_node_is_normalised() -> None:
    place = normalize_element(
        _node(
            1,
            {
                "name": "Fenton Cafe",
                "amenity": "cafe",
                "addr:housenumber": "821",
                "addr:street": "Fenton Street",
                "addr:city": "Silver Spring",
                "addr:state": "MD",
                "addr:postcode": "20910",
            },
        )
    )

    assert place is not None
    assert place.osm_id == "node/1"
    assert place.category == "Cafe"
    assert place.address == "821 Fenton Street, Silver Spring, MD 20910"
    assert place.source_tag == "amenity=cafe"


def test_way_uses_its_computed_centre() -> None:
    """Ways have no lat/lon of their own; `out center` supplies one."""
    place = normalize_element(
        {
            "type": "way",
            "id": 99,
            "center": {"lat": 38.993, "lon": -77.025},
            "tags": {"name": "Corner Market", "shop": "supermarket"},
        }
    )

    assert place is not None
    assert place.osm_id == "way/99"
    assert (place.latitude, place.longitude) == (38.993, -77.025)


@pytest.mark.parametrize(
    "tags",
    [
        {"name": "Partial", "amenity": "cafe", "addr:street": "Fenton Street"},
        {"name": "Partial", "amenity": "cafe", "addr:city": "Silver Spring"},
        {"name": "Partial", "amenity": "cafe"},
    ],
)
def test_missing_address_tags_are_tolerated(tags: dict[str, str]) -> None:
    """Most OSM POIs carry only some addr:* tags; none is mandatory."""
    place = normalize_element(_node(2, tags))

    assert place is not None
    assert place.address is None or "," not in place.address.strip(",")


def test_poi_with_no_address_tags_yields_none_not_stray_commas() -> None:
    place = normalize_element(_node(3, {"name": "No Address", "amenity": "cafe"}))

    assert place is not None
    assert place.address is None


def test_unnamed_poi_is_skipped() -> None:
    """An unnamed marker is one a user cannot act on."""
    assert normalize_element(_node(4, {"amenity": "cafe"})) is None


def test_poi_without_coordinates_is_skipped() -> None:
    assert normalize_element({"type": "way", "id": 5, "tags": {"name": "X", "shop": "books"}}) is None


def test_out_of_range_coordinates_are_skipped() -> None:
    element = _node(6, {"name": "Impossible", "amenity": "cafe"}, lat=91.0, lon=-77.0)

    assert normalize_element(element) is None


@pytest.mark.parametrize("element", [{}, {"type": "node"}, {"tags": {}}, "not a dict"])
def test_malformed_elements_are_skipped(element) -> None:
    assert normalize_element(element) is None


def test_original_tags_are_kept_as_evidence() -> None:
    place = normalize_element(
        _node(7, {"name": "Pho Place", "amenity": "restaurant", "cuisine": "vietnamese",
                  "opening_hours": "Mo-Su 11:00-22:00"})
    )

    assert place is not None
    assert place.tags == {"amenity": "restaurant", "cuisine": "vietnamese"}
    # Noise such as opening hours is not stored.
    assert "opening_hours" not in place.tags


# --- Client -----------------------------------------------------------------


def test_fetch_returns_normalised_places() -> None:
    handler = _ok(
        _node(1, {"name": "Cafe One", "amenity": "cafe"}),
        _node(2, {"name": "Bakery Two", "shop": "bakery"}),
        _node(3, {"amenity": "bench"}),  # not a business
    )

    places = _client(handler).fetch_places(FENTON_VILLAGE_BBOX)

    assert [p.name for p in places] == ["Cafe One", "Bakery Two"]


def test_duplicate_osm_ids_are_collapsed() -> None:
    """A way and node can describe the same establishment."""
    duplicate = _node(1, {"name": "Cafe One", "amenity": "cafe"})
    places = _client(_ok(duplicate, duplicate)).fetch_places(FENTON_VILLAGE_BBOX)

    assert len(places) == 1


def test_query_is_posted_as_form_data() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["body"] = request.content.decode()
        seen["agent"] = request.headers.get("user-agent", "")
        return httpx.Response(200, json=_payload())

    _client(handler).fetch_places(FENTON_VILLAGE_BBOX)

    assert seen["method"] == "POST"
    assert "out%3Ajson" in seen["body"] or "out:json" in seen["body"]
    # A descriptive User-Agent is expected of Overpass clients.
    assert "SilverSpringCommunityCensus" in seen["agent"]


def test_rate_limit_gives_an_actionable_error() -> None:
    client = _client(lambda request: httpx.Response(429, text="too many"))

    with pytest.raises(OverpassError, match="rate limit"):
        client.fetch_places(FENTON_VILLAGE_BBOX)


def test_gateway_timeout_suggests_a_smaller_box() -> None:
    client = _client(lambda request: httpx.Response(504, text="timeout"))

    with pytest.raises(OverpassError, match="smaller bounding box"):
        client.fetch_places(FENTON_VILLAGE_BBOX)


@pytest.mark.parametrize("status", [400, 403, 500])
def test_other_non_200_responses_raise(status: int) -> None:
    client = _client(lambda request: httpx.Response(status, text="nope"))

    with pytest.raises(OverpassError, match=str(status)):
        client.fetch_places(FENTON_VILLAGE_BBOX)


def test_non_json_response_raises() -> None:
    client = _client(lambda request: httpx.Response(200, text="<html>"))

    with pytest.raises(OverpassError, match="non-JSON"):
        client.fetch_places(FENTON_VILLAGE_BBOX)


def test_missing_element_list_raises() -> None:
    client = _client(lambda request: httpx.Response(200, json={"version": 0.6}))

    with pytest.raises(OverpassError, match="no element list"):
        client.fetch_places(FENTON_VILLAGE_BBOX)


def test_request_timeout_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(OverpassError, match="timed out"):
        _client(handler).fetch_places(FENTON_VILLAGE_BBOX)


# --- Ingestion --------------------------------------------------------------


def test_ingestion_stores_places_with_evidence(db_session: Session) -> None:
    handler = _ok(
        _node(1, {"name": "Cafe One", "amenity": "cafe", "cuisine": "coffee_shop"}),
        _node(2, {"name": "Bakery Two", "shop": "bakery"}),
    )

    report = ingest_businesses(db_session, _client(handler), FENTON_VILLAGE_BBOX)
    db_session.commit()

    assert report.fetched == 2
    assert report.inserted == 2
    assert report.updated == 0
    assert report.categories == {"Cafe": 1, "Bakery": 1}

    stored = BusinessRepository(db_session).search(query="Cafe One")[0]
    assert stored.external_id == "node/1"
    assert stored.category == "Cafe"
    assert stored.source_tag == "amenity=cafe"
    assert json.loads(stored.source_tags) == {
        "amenity": "cafe",
        "cuisine": "coffee_shop",
    }
    # OSM attribution, as the ODbL requires.
    assert stored.source == "OpenStreetMap contributors (node/1)"
    assert stored.source_url == "https://www.openstreetmap.org/copyright"
    assert stored.data_source.license.startswith("Open Database License")


def test_ingestion_is_idempotent(db_session: Session) -> None:
    handler = _ok(_node(1, {"name": "Cafe One", "amenity": "cafe"}))

    ingest_businesses(db_session, _client(handler), FENTON_VILLAGE_BBOX)
    db_session.commit()
    second = ingest_businesses(db_session, _client(handler), FENTON_VILLAGE_BBOX)
    db_session.commit()

    assert second.inserted == 0
    assert second.updated == 1
    assert BusinessRepository(db_session).count() == 1


def test_reingestion_updates_changed_fields(db_session: Session) -> None:
    """A renamed or re-tagged POI is refreshed, not duplicated."""
    ingest_businesses(
        db_session, _client(_ok(_node(1, {"name": "Old Name", "amenity": "cafe"}))),
        FENTON_VILLAGE_BBOX,
    )
    db_session.commit()

    ingest_businesses(
        db_session,
        _client(_ok(_node(1, {"name": "New Name", "shop": "bakery"}))),
        FENTON_VILLAGE_BBOX,
    )
    db_session.commit()

    businesses = BusinessRepository(db_session).list_all()
    assert len(businesses) == 1
    assert businesses[0].name == "New Name"
    assert businesses[0].category == "Bakery"


def test_report_counts_categories(db_session: Session) -> None:
    report = store_places(
        db_session,
        [
            p
            for p in (
                normalize_element(_node(1, {"name": "A", "amenity": "cafe"})),
                normalize_element(_node(2, {"name": "B", "amenity": "cafe"})),
                normalize_element(_node(3, {"name": "C", "shop": "florist"})),
            )
            if p is not None
        ],
    )
    db_session.commit()

    assert report.categories["Cafe"] == 2
    assert report.categories["Florist"] == 1


def test_stored_categories_are_all_frontend_filterable(db_session: Session) -> None:
    """End-to-end guard: nothing reaches the database that a chip cannot match."""
    handler = _ok(
        _node(1, {"name": "A", "amenity": "restaurant"}),
        _node(2, {"name": "B", "shop": "clothes"}),
        _node(3, {"name": "C", "office": "lawyer"}),
        _node(4, {"name": "D", "shop": "bicycle"}),
    )

    ingest_businesses(db_session, _client(handler), FENTON_VILLAGE_BBOX)
    db_session.commit()

    for business in BusinessRepository(db_session).list_all():
        assert business.category in FRONTEND_CATEGORIES


def test_failed_fetch_writes_nothing(db_session: Session) -> None:
    client = _client(lambda request: httpx.Response(503, text="down"))

    with pytest.raises(OverpassError):
        ingest_businesses(db_session, client, FENTON_VILLAGE_BBOX)
    db_session.rollback()

    assert BusinessRepository(db_session).count() == 0
