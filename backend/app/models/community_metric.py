"""A single measured value for a geography, inseparable from its evidence."""

from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.data_source import DataSource
from app.models.geography import Geography


class CommunityMetric(Base):
    """One metric value for one geography, from one dataset.

    ``data_source_id`` is NOT NULL by design. This is the core guarantee of
    the whole model: a metric cannot be written to the database without the
    dataset that backs it, so no value can reach the user unattributed. The
    evidence is a schema constraint, not a convention we have to remember.
    """

    __tablename__ = "community_metrics"
    __table_args__ = (
        # Re-running an ingestion must update, not duplicate. The same metric
        # for the same area from a *different* dataset or year is a distinct
        # legitimate row, so the source is part of the key.
        UniqueConstraint(
            "geography_id",
            "metric_key",
            "data_source_id",
            name="uq_community_metrics_geo_key_source",
        ),
        Index("ix_community_metrics_metric_key", "metric_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    geography_id: Mapped[int] = mapped_column(
        ForeignKey("geographies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    data_source_id: Mapped[int] = mapped_column(
        ForeignKey("data_sources.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    #: Stable internal name, e.g. "total_population", "median_household_income".
    metric_key: Mapped[str] = mapped_column(String(128), nullable=False)

    #: Nullable on purpose: the Census suppresses estimates for small
    #: populations. A missing value must be recorded as missing, never
    #: silently coerced to zero.
    value: Mapped[float | None] = mapped_column(Float, nullable=True)

    #: e.g. "people", "usd", "percent".
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)

    #: The provider's own variable for this row, e.g. the ACS code
    #: "B19013_001E". Row-specific, so it stays here rather than on
    #: DataSource.
    source_variable: Mapped[str | None] = mapped_column(String(128), nullable=True)

    geography: Mapped[Geography] = relationship(lazy="joined")
    data_source: Mapped[DataSource] = relationship(lazy="joined")

    # --- Evidence accessors -------------------------------------------------
    # Read-through properties so callers can reach citation fields directly
    # off the metric, without denormalising the columns onto this table.

    @property
    def dataset(self) -> str:
        return self.data_source.dataset

    @property
    def dataset_year(self) -> int | None:
        return self.data_source.dataset_year

    @property
    def source_url(self) -> str:
        return self.data_source.source_url

    def __repr__(self) -> str:
        return f"<CommunityMetric key={self.metric_key!r} value={self.value!r}>"
