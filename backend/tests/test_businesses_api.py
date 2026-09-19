"""Tests for the /businesses endpoint.

The assertions are written against the contract the frontend already
published in ``src/services/api.js``, so a breaking change here fails the
suite rather than showing up as an empty map.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.sample_data import seed


def test_returns_the_expected_envelope(client: TestClient, db_session: Session) -> None:
    """The frontend adapter reads payload.businesses."""
    seed(db_session)

    response = client.get("/businesses")

    assert response.status_code == 200
    assert "businesses" in response.json()


def test_empty_database_returns_an_empty_list_not_an_error(
    client: TestClient,
) -> None:
    """An empty result is a valid answer, not a 404."""
    response = client.get("/businesses")

    assert response.status_code == 200
    assert response.json()["businesses"] == []


def test_record_carries_every_field_the_frontend_requires(
    client: TestClient, db_session: Session
) -> None:
    """Contract fields from src/services/api.js normalizeBusinesses."""
    seed(db_session)

    record = client.get("/businesses").json()["businesses"][0]

    for field in ("id", "name", "category", "latitude", "longitude", "address", "source"):
        assert field in record, f"frontend adapter requires {field!r}"

    # Coordinates must be JSON numbers: the adapter discards records whose
    # coordinates are not finite numbers.
    assert isinstance(record["latitude"], (int, float))
    assert isinstance(record["longitude"], (int, float))
    assert isinstance(record["name"], str) and record["name"]


def test_record_carries_evidence_extras(
    client: TestClient, db_session: Session
) -> None:
    """Superset fields the current adapter ignores but can adopt later."""
    seed(db_session)

    record = client.get("/businesses").json()["businesses"][0]

    assert record["external_id"] == "test/1"
    assert record["source"] == "TEST Organization (test/1)"
    assert record["source_url"] == "https://example.invalid/test-dataset"
    assert record["dataset"] == "TEST Sample Dataset"


def test_category_filter(client: TestClient, db_session: Session) -> None:
    seed(db_session)

    assert len(client.get("/businesses?category=Cafe").json()["businesses"]) == 1
    assert client.get("/businesses?category=Bakery").json()["businesses"] == []


def test_name_search_is_case_insensitive(
    client: TestClient, db_session: Session
) -> None:
    seed(db_session)

    assert len(client.get("/businesses?q=sample").json()["businesses"]) == 1


def test_limit_is_bounded(client: TestClient, db_session: Session) -> None:
    """A rejected limit must be a 422, not an unbounded scan."""
    seed(db_session)

    assert client.get("/businesses?limit=1").status_code == 200
    assert client.get("/businesses?limit=0").status_code == 422
