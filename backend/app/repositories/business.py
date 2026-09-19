"""Persistence for :class:`~app.models.business.Business`."""

from __future__ import annotations

from sqlalchemy import func

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

    def category_counts(self) -> list[tuple[str, int]]:
        """Distinct categories present, with counts, most common first.

        Aggregated in the database rather than by loading every row, so the
        endpoint stays cheap as the dataset grows.
        """
        rows = (
            self.session.query(Business.category, func.count(Business.id))
            .group_by(Business.category)
            .order_by(func.count(Business.id).desc(), Business.category)
            .all()
        )
        return [(str(category), int(count)) for category, count in rows]

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
        source_tags: str | None = None,
        source_tag: str | None = None,
    ) -> tuple[Business, bool]:
        """Create the place, or update it in place if already ingested.

        Returns the row and whether it was newly created, so ingestion can
        report inserts and updates separately.
        """
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
            existing.source_tags = source_tags
            existing.source_tag = source_tag
            self.session.flush()
            return existing, False

        created = self.add(
            Business(
                data_source_id=data_source_id,
                external_id=external_id,
                name=name,
                category=category,
                latitude=latitude,
                longitude=longitude,
                address=address,
                geography_id=geography_id,
                source_tags=source_tags,
                source_tag=source_tag,
            )
        )
        return created, True
