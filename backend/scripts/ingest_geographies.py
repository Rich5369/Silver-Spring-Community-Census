"""Pre-fetch Census tract boundaries for the Silver Spring study area.

Run from the ``backend/`` directory, after ``ingest_census.py``::

    python scripts/ingest_geographies.py

Boundaries are cached into SQLite so that serving the map never contacts
TIGERweb. Idempotent: geometry is matched to existing geographies by GEOID
and overwritten in place.

Requires the Census metrics ingestion to have run first, because boundaries
are attached to geographies that ingestion created. Any GEOID returned by
TIGERweb with no matching row is reported rather than silently inserted - a
boundary with no metrics behind it would render as an empty shape on the map.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402
from app.core.database import SessionLocal, engine, init_database  # noqa: E402
from app.integrations.tigerweb import (  # noqa: E402
    FENTON_VILLAGE_STUDY_AREA,
    STUDY_AREA_DESCRIPTION,
    TIGERWEB_DATASET,
    TIGERWEB_LICENSE,
    TIGERWEB_ORGANIZATION,
    TigerWebClient,
)
from app.repositories import DataSourceRepository, GeographyRepository  # noqa: E402

GEOMETRY_SOURCE_KEY = "tigerweb-tracts-acs2024"


def main() -> int:
    """Fetch, store and report. Returns a process exit code."""
    settings = get_settings()
    client = TigerWebClient()

    print(f"Database   : {settings.database_url}")
    print(f"Source     : {client.layer_url}")
    print(f"Study area : {STUDY_AREA_DESCRIPTION}")
    print()

    init_database()
    session = SessionLocal()

    try:
        features = client.fetch_tracts(FENTON_VILLAGE_STUDY_AREA)
        print(f"TIGERweb returned {len(features)} tract(s).")

        source = DataSourceRepository(session).upsert(
            key=GEOMETRY_SOURCE_KEY,
            organization=TIGERWEB_ORGANIZATION,
            dataset=TIGERWEB_DATASET,
            dataset_year=2024,
            source_url=client.layer_url,
            license=TIGERWEB_LICENSE,
        )

        repository = GeographyRepository(session)
        matched: list[str] = []
        unmatched: list[str] = []

        for feature in features:
            geoid = str(feature.get("properties", {}).get("GEOID", "")).strip()
            geometry = feature.get("geometry")
            if not geoid or not isinstance(geometry, dict):
                continue

            updated = repository.set_geometry(
                geoid=geoid,
                geometry_geojson=json.dumps(geometry, separators=(",", ":")),
                geometry_source_id=source.id,
            )
            (matched if updated is not None else unmatched).append(geoid)

        session.commit()
    except Exception as exc:  # noqa: BLE001 - reported, not swallowed
        session.rollback()
        print(f"Ingestion failed: {exc}")
        return 1
    finally:
        session.close()
        engine.dispose()

    print(f"Boundaries stored : {len(matched)}")
    if unmatched:
        print(
            f"Unmatched GEOIDs  : {len(unmatched)} "
            f"(no metrics ingested for these) -> {', '.join(unmatched[:5])}"
        )
        print("  Run scripts/ingest_census.py first.")

    print("\nGeography ingestion complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
