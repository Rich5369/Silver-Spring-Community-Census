"""Shared pytest fixtures."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client() -> Iterator[TestClient]:
    """A test client backed by a freshly built application instance.

    Used as a context manager so that startup and shutdown hooks run, which
    makes the request tests double as a smoke test of application lifespan.
    """
    with TestClient(create_app()) as test_client:
        yield test_client
