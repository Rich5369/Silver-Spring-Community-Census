"""Provenance root: the dataset a stored fact came from."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DataSource(Base):
    """A citable dataset release.

    Normalised out of the fact tables because a single ingestion run produces
    hundreds of rows sharing one dataset, year and URL. Storing those strings
    per row would duplicate them and let them drift ("ACS 5-Year Estimates"
    vs "ACS5"). Facts that genuinely vary per row - such as the ACS variable
    a metric came from - stay on the fact table instead.
    """

    __tablename__ = "data_sources"
    __table_args__ = (UniqueConstraint("key", name="uq_data_sources_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    #: Stable slug identifying a dataset release, e.g. "acs5-2023".
    #: Used as the natural key so re-running ingestion updates rather than
    #: duplicating.
    key: Mapped[str] = mapped_column(String(128), nullable=False)

    organization: Mapped[str] = mapped_column(String(255), nullable=False)
    dataset: Mapped[str] = mapped_column(String(255), nullable=False)
    #: Null for continuously-edited sources such as OpenStreetMap.
    dataset_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    license: Mapped[str | None] = mapped_column(String(255), nullable=True)

    #: When this release was fetched - part of the citation, not bookkeeping.
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    def __repr__(self) -> str:
        return f"<DataSource key={self.key!r} year={self.dataset_year!r}>"
