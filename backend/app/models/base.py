"""Declarative base for all ORM models.

Domain tables are intentionally absent at this stage. When ingestion lands,
every fact-bearing table (Census ACS observations, OpenStreetMap places) will
carry a foreign key to a ``sources`` row so that no value can be stored, or
served, without the evidence that backs it.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base. Subclass this for every ORM model."""
