"""Shared pytest fixtures."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.main import create_app
from app.models import Base


@pytest.fixture
def client() -> Iterator[TestClient]:
    """A test client backed by a freshly built application instance.

    Used as a context manager so that startup and shutdown hooks run, which
    makes the request tests double as a smoke test of application lifespan.
    """
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture
def db_engine(tmp_path: Path) -> Iterator[Engine]:
    """An engine bound to a throwaway SQLite file, one per test.

    File-backed rather than in-memory so the tests exercise the same driver
    behaviour as the real service, including the ``PRAGMA foreign_keys``
    listener. ``tmp_path`` is unique per test, so tests never share state and
    the developer's ``data/community.db`` is never touched.
    """
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def db_session(db_engine: Engine) -> Iterator[Session]:
    """A session on the throwaway database."""
    factory = sessionmaker(bind=db_engine, autoflush=False, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()
