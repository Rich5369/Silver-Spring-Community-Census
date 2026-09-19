"""Persistence for :class:`~app.models.community_metric.CommunityMetric`."""

from __future__ import annotations

from app.models.community_metric import CommunityMetric
from app.repositories.base import BaseRepository


class CommunityMetricRepository(BaseRepository[CommunityMetric]):
    """Reads and upserts metric values.

    Every read returns the metric with its ``data_source`` eagerly loaded, so
    a caller always has the evidence in hand and cannot accidentally serve a
    number without it.
    """

    model = CommunityMetric

    def list_for_geography(self, geography_id: int) -> list[CommunityMetric]:
        """Every metric recorded for one area."""
        return list(
            self.session.query(CommunityMetric)
            .filter_by(geography_id=geography_id)
            .order_by(CommunityMetric.metric_key)
            .all()
        )

    def get_metric(
        self, *, geography_id: int, metric_key: str, data_source_id: int
    ) -> CommunityMetric | None:
        """Fetch the single row identified by the uniqueness constraint."""
        return (
            self.session.query(CommunityMetric)
            .filter_by(
                geography_id=geography_id,
                metric_key=metric_key,
                data_source_id=data_source_id,
            )
            .one_or_none()
        )

    def upsert(
        self,
        *,
        geography_id: int,
        data_source_id: int,
        metric_key: str,
        value: float | None,
        unit: str | None = None,
        source_variable: str | None = None,
    ) -> CommunityMetric:
        """Create the metric, or update the existing value in place.

        Keyed on (geography, metric, source) to match the table constraint, so
        re-running an ingestion refreshes values instead of accumulating
        duplicates.
        """
        existing = self.get_metric(
            geography_id=geography_id,
            metric_key=metric_key,
            data_source_id=data_source_id,
        )
        if existing is not None:
            existing.value = value
            existing.unit = unit
            existing.source_variable = source_variable
            self.session.flush()
            return existing

        return self.add(
            CommunityMetric(
                geography_id=geography_id,
                data_source_id=data_source_id,
                metric_key=metric_key,
                value=value,
                unit=unit,
                source_variable=source_variable,
            )
        )
