"""Read-only adapter for Montgomery County's official MC311 dataset."""

from __future__ import annotations

from functools import lru_cache

import httpx

from app.schemas.government import ServiceRequestResponse, ServiceRequestTrend

MC311_URL = "https://data.montgomerycountymd.gov/resource/xtyh-brr2.json"
MC311_SOURCE = "https://data.montgomerycountymd.gov/d/xtyh-brr2"


@lru_cache(maxsize=1)
def fetch_mc311_trend() -> ServiceRequestResponse:
    """Fetch annual MC311 volume for ZIP 20910, with a short-lived process cache.

    This is intentionally a read-only, aggregated request. The UI never sees
    resident-level records, and a source outage produces an explicit error
    rather than invented values.
    """
    params = {
        "$select": "date_extract_y(created) as year,count(*) as requests",
        "$where": 'x_zipcode="20910"',
        "$group": "year",
        "$order": "year",
    }
    try:
        response = httpx.get(MC311_URL, params=params, timeout=15.0,
                             headers={"User-Agent": "SilverSpringCommunityCensus/0.1"})
        response.raise_for_status()
        rows = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise RuntimeError("Montgomery County MC311 data is temporarily unavailable") from exc
    if not isinstance(rows, list):
        raise RuntimeError("Montgomery County MC311 returned an unexpected response")
    series = [
        ServiceRequestTrend(year=int(row["year"]), requests=int(row["requests"]))
        for row in rows if row.get("year") and row.get("requests")
    ]
    return ServiceRequestResponse(
        dataset="MC311 Service Requests",
        geography="Montgomery County ZIP 20910 (Silver Spring)",
        series=series,
        evidence=[{
            "organization": "Montgomery County, Maryland",
            "dataset": "MC311 Service Requests",
            "dataset_year": None,
            "geography": "ZIP 20910",
            "source_variable": "created, x_zipcode",
            "source_url": MC311_SOURCE,
        }],
        limitations=[
            "ZIP 20910 is a screening geography and is broader than Fenton Village.",
            "Request volume is not a direct measure of unmet need, service quality, or causation.",
            "The dataset is updated by the county; the latest year may be incomplete.",
        ],
    )
