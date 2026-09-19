"""Populate the database with ACS data for Montgomery County, Maryland.

Run from the ``backend/`` directory::

    python scripts/ingest_census.py
    python -m scripts.ingest_census --county-only

Idempotent: re-running refreshes values in place rather than duplicating
them, so it is safe to run repeatedly while iterating.

This is the only path by which Census data enters the system. Request
handlers read from the database and never call the Census API, so serving a
page cannot be blocked by an upstream outage or rate limit.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow `python scripts/ingest_census.py` as well as `python -m scripts...`.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402
from app.core.database import SessionLocal, engine, init_database  # noqa: E402
from app.integrations.census.client import CensusClient  # noqa: E402
from app.integrations.census.targets import (  # noqa: E402
    INGESTION_TARGETS,
    MONTGOMERY_COUNTY,
)
from app.integrations.census.variables import (  # noqa: E402
    ACS_DATASET,
    ACS_YEAR,
    METRIC_SPECS,
    required_variable_ids,
)
from app.services.census_ingest_service import ingest_targets  # noqa: E402


def build_client() -> CensusClient:
    """Construct the Census client from application settings.

    The key is unwrapped from ``SecretStr`` here, at the single point of use,
    and is never printed.
    """
    settings = get_settings()
    api_key = (
        settings.census_api_key.get_secret_value()
        if settings.has_census_api_key
        else None
    )
    return CensusClient(year=ACS_YEAR, dataset=ACS_DATASET, api_key=api_key)


def main(argv: list[str] | None = None) -> int:
    """Run ingestion and print a report. Returns a process exit code."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--county-only",
        action="store_true",
        help="Ingest only the county total, skipping the ~200 tract rows.",
    )
    args = parser.parse_args(argv)

    settings = get_settings()
    targets = (
        (("Montgomery County", MONTGOMERY_COUNTY),)
        if args.county_only
        else INGESTION_TARGETS
    )

    print(f"ACS release : {ACS_YEAR} {ACS_DATASET}")
    print(f"Database    : {settings.database_url}")
    # Whether a key is configured is useful; the key itself is never shown.
    print(f"API key     : {'configured' if settings.has_census_api_key else 'none'}")
    print(f"Variables   : {len(required_variable_ids())}")
    print(f"Metrics     : {len(METRIC_SPECS)}")
    print(f"Targets     : {', '.join(label for label, _ in targets)}")
    print()

    init_database()

    session = SessionLocal()
    try:
        report = ingest_targets(session, build_client(), targets)
    finally:
        session.close()
        engine.dispose()

    print(f"Geographies      : {report.geographies}")
    print(f"Metrics stored   : {report.metrics_written}")
    print(f"Metrics missing  : {report.metrics_missing} (suppressed or unavailable)")

    if report.errors:
        print("\nErrors:")
        for error in report.errors:
            print(f"  - {error}")
        return 1

    print("\nIngestion complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
