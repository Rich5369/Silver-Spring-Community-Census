"""Fetch Fenton Village business POIs from OpenStreetMap into the database.

Run from the ``backend/`` directory::

    python scripts/ingest_businesses.py

Idempotent: keyed on the OSM element id, so re-running refreshes existing
rows instead of duplicating them.

Overpass is free, shared, volunteer-run infrastructure. This script is the
only thing that talks to it; request handlers read from SQLite.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402
from app.core.database import SessionLocal, engine, init_database  # noqa: E402
from app.integrations.overpass import (  # noqa: E402
    FENTON_VILLAGE_BBOX,
    OverpassClient,
)
from app.services.business_ingest_service import ingest_businesses  # noqa: E402


def main() -> int:
    """Run ingestion and print a summary. Returns a process exit code."""
    settings = get_settings()
    box = FENTON_VILLAGE_BBOX

    print(f"Database  : {settings.database_url}")
    print("Source    : OpenStreetMap via Overpass API")
    print(
        f"Bounding box : lon {box.min_lon} to {box.max_lon}, "
        f"lat {box.min_lat} to {box.max_lat} (Fenton Village)"
    )
    print()

    init_database()
    session = SessionLocal()

    try:
        report = ingest_businesses(session, OverpassClient(), box)
        session.commit()
    except Exception as exc:  # noqa: BLE001 - reported, not swallowed
        session.rollback()
        print(f"Ingestion failed: {exc}")
        return 1
    finally:
        session.close()
        engine.dispose()

    print(f"Fetched   : {report.fetched}")
    print(f"Inserted  : {report.inserted}")
    print(f"Updated   : {report.updated}")
    print("\nCategories:")
    for category, count in report.categories.most_common():
        print(f"  {category:24} {count}")

    print("\nBusiness ingestion complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
