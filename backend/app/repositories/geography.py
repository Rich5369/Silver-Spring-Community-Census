"""Persistence for :class:`~app.models.geography.Geography`."""

from __future__ import annotations

from app.models.geography import Geography
from app.repositories.base import BaseRepository


class GeographyRepository(BaseRepository[Geography]):
    """Reads and upserts geographic areas."""

    model = Geography

    def get_by_geoid(self, geoid: str) -> Geography | None:
        """Fetch an area by its canonical identifier."""
        return self.session.query(Geography).filter_by(geoid=geoid).one_or_none()

    def list_by_type(self, geography_type: str) -> list[Geography]:
        """All areas of one type, e.g. every ``"tract"``."""
        return list(
            self.session.query(Geography)
            .filter_by(geography_type=geography_type)
            .order_by(Geography.name)
            .all()
        )

    def upsert(
        self,
        *,
        geoid: str,
        name: str,
        geography_type: str,
        state_fips: str | None = None,
        county_fips: str | None = None,
        tract_code: str | None = None,
        block_group_code: str | None = None,
        geometry_geojson: str | None = None,
    ) -> Geography:
        """Create the area, or update it in place if ``geoid`` already exists."""
        existing = self.get_by_geoid(geoid)
        if existing is not None:
            existing.name = name
            existing.geography_type = geography_type
            existing.state_fips = state_fips
            existing.county_fips = county_fips
            existing.tract_code = tract_code
            existing.block_group_code = block_group_code
            # Only overwrite geometry when new geometry is supplied, so a
            # metadata-only refresh cannot wipe a boundary already loaded.
            if geometry_geojson is not None:
                existing.geometry_geojson = geometry_geojson
            self.session.flush()
            return existing

        return self.add(
            Geography(
                geoid=geoid,
                name=name,
                geography_type=geography_type,
                state_fips=state_fips,
                county_fips=county_fips,
                tract_code=tract_code,
                block_group_code=block_group_code,
                geometry_geojson=geometry_geojson,
            )
        )
