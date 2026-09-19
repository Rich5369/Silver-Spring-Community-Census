"""Read-only adapter for Montgomery County's official MC311 dataset."""

from __future__ import annotations

import json
from pathlib import Path
import time

import httpx

from app.schemas.government import ServiceRequestResponse, ServiceRequestTrend

MC311_URL = "https://data.montgomerycountymd.gov/resource/xtyh-brr2.json"
MC311_SOURCE = "https://data.montgomerycountymd.gov/d/xtyh-brr2"
SNAPSHOT_PATH = Path(__file__).resolve().parents[2] / "data" / "mc311_20910.json"
SNAPSHOT_ROWS = [
    {"year": str(year), "requests": str(requests)}
    for year, requests in (
        (2012, 4152), (2013, 7928), (2014, 9792), (2015, 11392),
        (2016, 12358), (2017, 13614), (2018, 12222), (2019, 12391),
        (2020, 13931), (2021, 13671), (2022, 13538), (2023, 12502),
        (2024, 12740), (2025, 14338), (2026, 11555),
    )
]

_CACHE_TTL_SECONDS = 900
_cached_response: tuple[float, ServiceRequestResponse] | None = None


def fetch_mc311_trend() -> ServiceRequestResponse:
    """Fetch annual MC311 volume for ZIP 20910, with a short-lived process cache.

    This is intentionally a read-only, aggregated request. The UI never sees
    resident-level records, and a source outage produces an explicit error
    rather than invented values.
    """
    global _cached_response
    now = time.monotonic()
    if _cached_response and now - _cached_response[0] < _CACHE_TTL_SECONDS:
        return _cached_response[1]

    params = {
        "$select": "date_extract_y(created) as year,count(*) as requests",
        "$where": 'x_zipcode="20910"',
        "$group": "year",
        "$order": "year",
    }
    try:
        response = httpx.get(MC311_URL, params=params, timeout=5.0,
                             headers={"User-Agent": "SilverSpringCommunityCensus/0.1"})
        response.raise_for_status()
        rows = response.json()
    except Exception:
        # Render/free hosting and the county portal can have transient network
        # failures. Keep the demo honest and usable with a dated, committed
        # snapshot instead of returning a misleading 500 or invented values.
        try:
            rows = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            # Keep the release self-contained even if a deployment omits the
            # optional fixture file. These values are the same dated official
            # snapshot, and the response remains explicitly labelled.
            rows = SNAPSHOT_ROWS
        source_status = "dated_snapshot"
    else:
        source_status = "live"
    if not isinstance(rows, list):
        raise RuntimeError("Montgomery County MC311 returned an unexpected response")
    series = [
        ServiceRequestTrend(year=int(row["year"]), requests=int(row["requests"]))
        for row in rows if row.get("year") and row.get("requests")
    ]
    result = ServiceRequestResponse(
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
            *( ["Live county endpoint was unavailable; values are the committed 2026-09-19 snapshot."] if source_status == "dated_snapshot" else [] ),
        ],
        source_status=source_status,
    )
    _cached_response = (time.monotonic(), result)
    return result
