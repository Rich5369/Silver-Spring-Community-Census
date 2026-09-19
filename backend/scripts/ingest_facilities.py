"""Ingest civic facilities from OpenStreetMap/Overpass into the database."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.database import SessionLocal, engine, init_database
from app.integrations.overpass import FENTON_VILLAGE_BBOX, OSM_ATTRIBUTION_URL, OSM_DATASET, OSM_LICENSE, OSM_ORGANIZATION, OverpassClient
from app.models import DataSource, Facility
from app.repositories.data_source import DataSourceRepository

def main() -> int:
    init_database(); session = SessionLocal()
    try:
        source = DataSourceRepository(session).upsert(key="openstreetmap-facilities", organization=OSM_ORGANIZATION, dataset=f"{OSM_DATASET} (civic facilities)", source_url=OSM_ATTRIBUTION_URL, license=OSM_LICENSE)
        places = OverpassClient().fetch_facilities(FENTON_VILLAGE_BBOX)
        for place in places:
            row = session.query(Facility).filter_by(data_source_id=source.id, external_id=place.osm_id).one_or_none()
            if row is None:
                row = Facility(data_source_id=source.id, external_id=place.osm_id)
                session.add(row)
            row.name, row.facility_type = place.name, place.category
            row.latitude, row.longitude, row.address = place.latitude, place.longitude, place.address
        session.commit(); print(f"Facilities stored: {len(places)}")
    finally:
        session.close(); engine.dispose()
    return 0
if __name__ == "__main__": raise SystemExit(main())
