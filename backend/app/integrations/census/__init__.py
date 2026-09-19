"""US Census Data API integration.

Fetching (:mod:`client`), transformation (:mod:`transform`) and the variable
catalogue (:mod:`variables`) are separate modules. Persistence is deliberately
not here - it lives in :mod:`app.services.census_ingest_service`.
"""

from app.integrations.census.client import (
    CensusApiError,
    CensusClient,
    GeographyQuery,
    redact,
)
from app.integrations.census.transform import (
    GeographyRecord,
    MetricRecord,
    compute_metrics,
    parse_geography,
    parse_value,
)
from app.integrations.census.variables import (
    ACS_DATASET,
    ACS_DATASET_TITLE,
    ACS_VARIABLES,
    ACS_YEAR,
    METRIC_SPECS,
    MetricSpec,
    required_variable_ids,
)

__all__ = [
    "ACS_DATASET",
    "ACS_DATASET_TITLE",
    "ACS_VARIABLES",
    "ACS_YEAR",
    "CensusApiError",
    "CensusClient",
    "GeographyQuery",
    "GeographyRecord",
    "METRIC_SPECS",
    "MetricRecord",
    "MetricSpec",
    "compute_metrics",
    "parse_geography",
    "parse_value",
    "redact",
    "required_variable_ids",
]
