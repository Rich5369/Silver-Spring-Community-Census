"""Base repository.

Repositories own persistence access so that services and route handlers stay
free of SQLAlchemy query construction and can be tested against fakes.
"""

from __future__ import annotations

from typing import Generic, TypeVar

from sqlalchemy.orm import Session

from app.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Holds the session and model a concrete repository works against.

    Repositories deliberately do **not** commit. The caller owns the
    transaction boundary, so a multi-step ingestion can write several tables
    and commit once, or roll the whole thing back.
    """

    model: type[ModelT]

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, row_id: int) -> ModelT | None:
        """Fetch one row by primary key, or ``None``."""
        return self.session.get(self.model, row_id)

    def list_all(self) -> list[ModelT]:
        """Fetch every row. Intended for small reference tables only."""
        return list(self.session.query(self.model).all())

    def add(self, instance: ModelT) -> ModelT:
        """Stage a new row and flush so its primary key is populated."""
        self.session.add(instance)
        self.session.flush()
        return instance

    def count(self) -> int:
        """Number of rows in the table."""
        return self.session.query(self.model).count()
