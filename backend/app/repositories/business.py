"""Persistence for :class:`~app.models.business.Business`."""

from __future__ import annotations

from app.models.business import Business
from app.repositories.base import BaseRepository


class BusinessRepository(BaseRepository[Business]):
    """Reads and upserts mappable places."""

    model = Business

    def get_by_external_id(
        self, *, data_source_id: int, external_id: str
    ) -> Business | None:
        """Fetch the row identified by the uniqueness constraint."""
        return (
            self.session.query(Business)
            .filter_by(data_source_id=data_source_id, external_id=external_id)
            .one_or_none()
        )

    def search(
        self,
        *,
        category: str | None = None,
        query: str | None = None,
        limit: int | None = None,
    ) -> list[Business]:
        """Filter places by category and/or a case-insensitive name match.

        This is the query logic the ``/businesses`` route will call. Keeping
        it here means the handler stays a transport shim with no SQL in it.
        """
        stmt = self.session.query(Business)

        if category:
            stmt = stmt.filter(Business.category == category)
        if query:
            # ``ilike`` degrades to a case-insensitive LIKE on SQLite, which
            # is what we want; escaping the wildcards keeps a user-supplied
            # "%" from matching everything.
            escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            stmt = stmt.filter(Business.name.ilike(f"%{escaped}%", escape="\\"))

        stmt = stmt.order_by(Business.name)
        if limit is not None:
            stmt = stmt.limit(limit)
        return list(stmt.all())

    def upsert(
        self,
        *,
        data_source_id: int,
        external_id: str,
        name: str,
        category: str,
        latitude: float,
        longitude: float,
        address: str | None = None,
        geography_id: int | None = None,
    ) -> Business:
        """Create the place, or update it in place if already ingested."""
        existing = self.get_by_external_id(
            data_source_id=data_source_id, external_id=external_id
        )
        if existing is not None:
            existing.name = name
            existing.category = category
            existing.latitude = latitude
            existing.longitude = longitude
            existing.address = address
            existing.geography_id = geography_id
            self.session.flush()
            return existing

        return self.add(
            Business(
                data_source_id=data_source_id,
                external_id=external_id,
                name=name,
                category=category,
                latitude=latitude,
                longitude=longitude,
                address=address,
                geography_id=geography_id,
            )
        )
