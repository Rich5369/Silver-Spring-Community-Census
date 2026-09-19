"""Persistence for :class:`~app.models.data_source.DataSource`."""

from __future__ import annotations

from app.models.data_source import DataSource
from app.repositories.base import BaseRepository


class DataSourceRepository(BaseRepository[DataSource]):
    """Reads and upserts citable dataset releases."""

    model = DataSource

    def get_by_key(self, key: str) -> DataSource | None:
        """Fetch a source by its stable slug, e.g. ``"acs5-2023"``."""
        return self.session.query(DataSource).filter_by(key=key).one_or_none()

    def upsert(
        self,
        *,
        key: str,
        organization: str,
        dataset: str,
        source_url: str,
        dataset_year: int | None = None,
        license: str | None = None,
    ) -> DataSource:
        """Create the source, or update it in place if ``key`` already exists.

        Makes ingestion idempotent: re-running it refreshes the citation
        rather than creating a second row that existing metrics do not point
        at.
        """
        existing = self.get_by_key(key)
        if existing is not None:
            existing.organization = organization
            existing.dataset = dataset
            existing.source_url = source_url
            existing.dataset_year = dataset_year
            existing.license = license
            self.session.flush()
            return existing

        return self.add(
            DataSource(
                key=key,
                organization=organization,
                dataset=dataset,
                source_url=source_url,
                dataset_year=dataset_year,
                license=license,
            )
        )
