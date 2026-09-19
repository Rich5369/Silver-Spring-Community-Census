"""Tests for ``GET /health``.

The health endpoint is the frontend's and the demo operator's signal that the
backend is reachable, so its contract is pinned here: exact status code, exact
payload shape, and working CORS headers.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import get_settings


def test_health_returns_ok(client: TestClient) -> None:
    """The endpoint responds 200 with the agreed payload."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "community-intelligence-api",
    }


def test_health_reports_configured_service_name(client: TestClient) -> None:
    """The service name is sourced from settings, not hardcoded in the route."""
    response = client.get("/health")

    assert response.json()["service"] == get_settings().service_name


def test_health_allows_frontend_origin(client: TestClient) -> None:
    """A browser request from the Vite dev server is permitted by CORS.

    Without this the frontend silently falls back to its demo data, which is
    an easy failure to miss during a live demo.
    """
    origin = "http://localhost:5173"
    response = client.get("/health", headers={"Origin": origin})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
