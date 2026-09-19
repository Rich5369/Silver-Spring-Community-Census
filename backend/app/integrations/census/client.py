"""HTTP client for the US Census Data API.

Fetching only: this module returns raw rows and knows nothing about our
models or database. Transformation lives in
:mod:`app.integrations.census.transform`, persistence in
:mod:`app.services.census_ingest_service`.

**This client is never called from a request handler.** Census data is
ingested into SQLite by ``scripts/ingest_census.py`` and served from there,
so a demo is never at the mercy of an upstream outage or rate limit.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

# The API accepts at most 50 variables per request.
MAX_VARIABLES_PER_REQUEST: int = 45

CENSUS_API_ROOT: str = "https://api.census.gov/data"


class CensusApiError(RuntimeError):
    """A Census request failed or returned something unusable.

    Messages are always built from redacted URLs. Never re-raise an httpx
    error directly: ``response.raise_for_status()`` embeds the full request
    URL, which contains the API key, in the exception text and therefore in
    any log or traceback.
    """


@dataclass(frozen=True)
class GeographyQuery:
    """A Census geography selector.

    ``for_clause`` and ``in_clause`` map onto the API's ``for``/``in``
    parameters, e.g. ``for_clause="tract:*"`` with
    ``in_clause="state:24 county:031"``.
    """

    for_clause: str
    in_clause: str | None = None


def redact(url: str | httpx.URL) -> str:
    """Strip the API key from a URL so it is safe to log or raise."""
    text = str(url)
    parts = text.split("key=", 1)
    if len(parts) == 1:
        return text
    tail = parts[1].split("&", 1)
    remainder = f"&{tail[1]}" if len(tail) > 1 else ""
    return f"{parts[0]}key=REDACTED{remainder}"


class CensusClient:
    """Reads variable values from one ACS release.

    Args:
        year: ACS release year, e.g. 2024.
        dataset: Dataset path, e.g. ``"acs/acs5"``.
        api_key: Optional for runtime and tests. The upstream API may require
            one when running a fresh ingestion.
        timeout: Explicit connect/read/write/pool timeouts. The Census API
            can be slow for large tract queries, so the read timeout is
            generous while the connect timeout stays short.
    """

    def __init__(
        self,
        *,
        year: int,
        dataset: str,
        api_key: str | None = None,
        timeout: httpx.Timeout | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.year = year
        self.dataset = dataset
        self._api_key = api_key
        self._timeout = timeout or httpx.Timeout(
            connect=10.0, read=60.0, write=10.0, pool=10.0
        )
        self._transport = transport

    @property
    def base_url(self) -> str:
        """Citable dataset endpoint, containing no credentials."""
        return f"{CENSUS_API_ROOT}/{self.year}/{self.dataset}"

    def _build_params(
        self, variables: list[str], geography: GeographyQuery
    ) -> dict[str, str]:
        params = {"get": ",".join(["NAME", *variables]), "for": geography.for_clause}
        if geography.in_clause:
            params["in"] = geography.in_clause
        if self._api_key:
            params["key"] = self._api_key
        return params

    def _request(
        self, variables: list[str], geography: GeographyQuery
    ) -> list[list[str]]:
        """Perform one request and return the raw Census matrix."""
        params = self._build_params(variables, geography)
        try:
            with httpx.Client(
                timeout=self._timeout,
                transport=self._transport,
                follow_redirects=True,
            ) as client:
                response = client.get(self.base_url, params=params)
        except httpx.TimeoutException as exc:
            raise CensusApiError(
                f"Census request timed out after {self._timeout.read}s "
                f"for {redact(self.base_url)}"
            ) from exc
        except httpx.HTTPError as exc:
            # str(exc) can contain the request URL, so it is redacted too.
            raise CensusApiError(
                f"Census request failed: {redact(str(exc))}"
            ) from exc

        if response.url.path.endswith("/missing_key.html"):
            raise CensusApiError(
                "Census API rejected the unkeyed ingestion request. Set "
                "CENSUS_API_KEY in backend/.env, or use a populated "
                "backend/data/community.db from a teammate. The key is not "
                "needed when serving data already stored in SQLite."
            )

        if response.status_code != 200:
            # Deliberately not raise_for_status(): it leaks the key.
            body = response.text[:200].replace("\n", " ")
            raise CensusApiError(
                f"Census API returned HTTP {response.status_code} for "
                f"{redact(response.request.url)}: {body}"
            )

        try:
            payload: Any = response.json()
        except ValueError as exc:
            raise CensusApiError(
                f"Census API returned non-JSON content for "
                f"{redact(response.request.url)}"
            ) from exc

        if not isinstance(payload, list) or len(payload) < 1:
            raise CensusApiError(
                f"Census API returned an unexpected payload shape for "
                f"{redact(response.request.url)}"
            )
        if not all(isinstance(row, list) for row in payload):
            raise CensusApiError(
                f"Census API returned a malformed matrix for "
                f"{redact(response.request.url)}"
            )
        return payload

    def fetch(
        self, variables: list[str], geography: GeographyQuery
    ) -> list[dict[str, str]]:
        """Fetch variables for a geography as a list of row dictionaries.

        Requests are split into chunks under the API's per-request variable
        limit and merged on the geography identifier columns, so callers can
        ask for an arbitrary number of variables.

        Returns one dict per geography, mapping column name to raw string
        value. Values are left exactly as the API returned them; converting
        and validating them is the transformer's job.
        """
        if not variables:
            raise ValueError("At least one variable is required.")

        merged: dict[tuple[str, ...], dict[str, str]] = {}
        geo_columns: list[str] = []

        for start in range(0, len(variables), MAX_VARIABLES_PER_REQUEST):
            chunk = variables[start : start + MAX_VARIABLES_PER_REQUEST]
            matrix = self._request(chunk, geography)
            header, *rows = matrix

            # Geography identifier columns are whatever is not NAME or a
            # requested variable, e.g. state / county / tract.
            requested = {"NAME", *chunk}
            geo_columns = [column for column in header if column not in requested]

            for row in rows:
                if len(row) != len(header):
                    # A short row cannot be aligned to its header; skipping
                    # is safer than silently mis-assigning values.
                    continue
                record = dict(zip(header, row, strict=True))
                key = tuple(record[column] for column in geo_columns)
                merged.setdefault(key, {}).update(record)

        return list(merged.values())
