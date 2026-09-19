"""Persist OpenStreetMap business POIs.

The third stage: Overpass fetches, ``osm_categories`` normalises, this
service writes.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.integrations.geo import BoundingBox
from app.integrations.overpass import (
    OSM_ATTRIBUTION_URL,
    OSM_DATASET,
    OSM_LICENSE,
    OSM_ORGANIZATION,
    OverpassClient,
    OsmPlace,
)
from app.models import DataSource
from app.repositories import BusinessRepository, DataSourceRepository

OSM_SOURCE_KEY = "openstreetmap-overpass"


@dataclass
class BusinessIngestionReport:
    """What one ingestion run did, for the CLI to print."""

    fetched: int = 0
    inserted: int = 0
    updated: int = 0
    categories: Counter[str] = field(default_factory=Counter)


def register_data_source(session: Session) -> DataSource:
    """Create or refresh the OSM citation row.

    The source URL is the ODbL attribution page rather than the Overpass
    endpoint: it is what OSM's licence asks be shown to users, and it stays
    valid regardless of which Overpass mirror was queried.
    """
    return DataSourceRepository(session).upsert(
        key=OSM_SOURCE_KEY,
        organization=OSM_ORGANIZATION,
        dataset=OSM_DATASET,
        dataset_year=None,  # OSM is continuously edited; it has no vintage.
        source_url=OSM_ATTRIBUTION_URL,
        license=OSM_LICENSE,
    )


def store_places(
    session: Session, places: list[OsmPlace]
) -> BusinessIngestionReport:
    """Write normalised POIs, reporting inserts and updates separately.

    Idempotent: keyed on (data source, OSM id), so re-running refreshes rows
    rather than duplicating them. The caller commits.
    """
    report = BusinessIngestionReport(fetched=len(places))
    source = register_data_source(session)
    repository = BusinessRepository(session)

    for place in places:
        _, created = repository.upsert(
            data_source_id=source.id,
            external_id=place.osm_id,
            name=place.name,
            category=place.category,
            latitude=place.latitude,
            longitude=place.longitude,
            address=place.address,
            source_tags=json.dumps(place.tags, sort_keys=True) if place.tags else None,
            source_tag=place.source_tag,
        )
        if created:
            report.inserted += 1
        else:
            report.updated += 1
        report.categories[place.category] += 1

    return report


def ingest_businesses(
    session: Session, client: OverpassClient, bbox: BoundingBox
) -> BusinessIngestionReport:
    """Fetch POIs for ``bbox`` and store them."""
    return store_places(session, client.fetch_places(bbox))
