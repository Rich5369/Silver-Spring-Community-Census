"""Base repository.

Repositories own persistence access so that services stay free of SQLAlchemy
query construction and can be tested against fakes. No concrete repositories
exist yet; the first will read Census observations and OpenStreetMap places
alongside their source records.
"""

from __future__ import annotations

from sqlalchemy.orm import Session


class BaseRepository:
    """Holds the session a concrete repository works against."""

    def __init__(self, session: Session) -> None:
        self.session = session
