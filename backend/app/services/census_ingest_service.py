"""Persist Census data into the database.

The third stage of the pipeline: the client fetches, the transformer
computes, this service writes. Keeping persistence separate means the
arithmetic can be tested without a database and the writes can be tested
without the network.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.integrations.census.client import CensusClient, GeographyQuery
from app.integrations.census.transform import compute_metrics, parse_geography
from app.integrations.census.variables import (
    ACS_DATASET_TITLE,
    ACS_YEAR,
    required_variable_ids,
)
from app.models import DataSource
from app.repositories import (
    CommunityMetricRepository,
    DataSourceRepository,
    GeographyRepository,
)

CENSUS_ORGANIZATION = "US Census Bureau"
CENSUS_LICENSE = "Public domain (US Government work)"


@dataclass
class IngestionReport:
    """What one ingestion run did, for the CLI to print."""

    geographies: int = 0
    metrics_written: int = 0
    metrics_missing: int = 0
    errors: list[str] = field(default_factory=list)

    def merge(self, other: IngestionReport) -> None:
        self.geographies += other.geographies
        self.metrics_written += other.metrics_written
        self.metrics_missing += other.metrics_missing
        self.errors.extend(other.errors)


def data_source_key(year: int = ACS_YEAR) -> str:
    """Stable slug for an ACS release, e.g. ``"acs5-2024"``."""
    return f"acs5-{year}"


def register_data_source(session: Session, client: CensusClient) -> DataSource:
    """Create or refresh the citation row for this ACS release.

    ``client.base_url`` carries no credentials, so it is safe to store and to
    show to a user as the source link.
    """
    return DataSourceRepository(session).upsert(
        key=data_source_key(client.year),
        organization=CENSUS_ORGANIZATION,
        dataset=f"{ACS_DATASET_TITLE} ({client.year})",
        dataset_year=client.year,
        source_url=client.base_url,
        license=CENSUS_LICENSE,
    )


def ingest_geography(
    session: Session,
    client: CensusClient,
    geography: GeographyQuery,
) -> IngestionReport:
    """Fetch, transform and store every metric for one geography selector.

    Idempotent: geographies are upserted on GEOID and metrics on
    (geography, metric_key, data_source), so re-running refreshes values
    rather than accumulating duplicates. The caller commits.
    """
    report = IngestionReport()

    source = register_data_source(session, client)
    rows = client.fetch(list(required_variable_ids()), geography)

    geography_repo = GeographyRepository(session)
    metric_repo = CommunityMetricRepository(session)

    for row in rows:
        parsed = parse_geography(row)
        stored_geography = geography_repo.upsert(
            geoid=parsed.geoid,
            name=parsed.name,
            geography_type=parsed.geography_type,
            state_fips=parsed.state_fips,
            county_fips=parsed.county_fips,
            tract_code=parsed.tract_code,
        )
        report.geographies += 1

        for record in compute_metrics(row):
            # Suppressed metrics are stored with a NULL value rather than
            # skipped, so the profile can say "not available for this tract"
            # instead of silently omitting the row.
            if record.value is None:
                report.metrics_missing += 1
            else:
                report.metrics_written += 1

            metric_repo.upsert(
                geography_id=stored_geography.id,
                data_source_id=source.id,
                metric_key=record.metric_key,
                value=record.value,
                unit=record.unit,
                source_variable=record.source_variable,
            )

    return report


def ingest_targets(
    session: Session,
    client: CensusClient,
    targets: tuple[tuple[str, GeographyQuery], ...],
) -> IngestionReport:
    """Ingest several geography selectors, committing once per target.

    Committing per target rather than per run means a failure partway through
    leaves the completed targets intact instead of discarding everything.
    """
    total = IngestionReport()

    for label, geography in targets:
        try:
            result = ingest_geography(session, client, geography)
            session.commit()
            total.merge(result)
        except Exception as exc:  # noqa: BLE001 - reported, not swallowed
            session.rollback()
            total.errors.append(f"{label}: {exc}")

    return total
