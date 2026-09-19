"""A mappable business or place, inseparable from its evidence."""

from __future__ import annotations

from sqlalchemy import (
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.data_source import DataSource
from app.models.geography import Geography


class Business(Base):
    """A business or community place shown on the map.

    Like :class:`~app.models.community_metric.CommunityMetric`, the link to a
    data source is NOT NULL: nothing is placed on the map that cannot be
    attributed.
    """

    __tablename__ = "businesses"
    __table_args__ = (
        # An upstream record maps to exactly one row per source, so
        # re-ingesting an OSM extract updates rather than duplicating.
        UniqueConstraint(
            "data_source_id", "external_id", name="uq_businesses_source_external_id"
        ),
        # Cheap guards against transposed or malformed coordinates, which
        # otherwise surface as markers in the ocean.
        CheckConstraint(
            "latitude BETWEEN -90 AND 90", name="ck_businesses_latitude_range"
        ),
        CheckConstraint(
            "longitude BETWEEN -180 AND 180", name="ck_businesses_longitude_range"
        ),
        Index("ix_businesses_category", "category"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    data_source_id: Mapped[int] = mapped_column(
        ForeignKey("data_sources.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    #: The provider's identifier, e.g. the OSM element "node/1234567".
    #: Doubles as the citation anchor for this specific record.
    external_id: Mapped[str] = mapped_column(String(128), nullable=False)

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    #: Normalised display category. Ingestion must map upstream tags onto the
    #: vocabulary the frontend filters by (Restaurant, Cafe, Bakery, Retail,
    #: Grocery, ...), or its filter chips silently return nothing.
    category: Mapped[str] = mapped_column(String(64), nullable=False)

    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)

    address: Mapped[str | None] = mapped_column(Text, nullable=True)

    #: The upstream tags this record was classified from, as JSON, plus the
    #: single ``key=value`` that decided the category. Kept as evidence: our
    #: taxonomy is a lossy mapping of a far richer tag vocabulary, and
    #: without the original a surprising category is untraceable.
    source_tags: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_tag: Mapped[str | None] = mapped_column(String(128), nullable=True)

    #: Optional link to the area this place falls within, set during
    #: ingestion. Nullable because a place can be ingested before the
    #: geography it belongs to is resolved.
    geography_id: Mapped[int | None] = mapped_column(
        ForeignKey("geographies.id", ondelete="SET NULL"), nullable=True, index=True
    )

    data_source: Mapped[DataSource] = relationship(lazy="joined")
    geography: Mapped[Geography | None] = relationship(lazy="joined")

    # --- Evidence accessors -------------------------------------------------

    @property
    def source(self) -> str:
        """Human-readable attribution for display in a map popup."""
        return f"{self.data_source.organization} ({self.external_id})"

    @property
    def source_url(self) -> str:
        return self.data_source.source_url

    def __repr__(self) -> str:
        return f"<Business name={self.name!r} category={self.category!r}>"
