"""Census TIGERweb client for tract boundary geometry.

TIGERweb is the Census Bureau's own ArcGIS service for TIGER/Line geography.
It returns GeoJSON directly, so no shapefile parsing and no GIS dependency
(geopandas, shapely, pyshp) is needed - useful given the whole MVP runs on
SQLite.

The service is pinned to the **ACS 2024 vintage**, matching the ACS 2024
5-Year estimates ingested by ``scripts/ingest_census.py``. Tract boundaries
change between vintages, so pairing 2024 estimates with "current" boundaries
would silently mismatch areas. The alternative ``tigerWMS_Current`` service
is deliberately not used.

**Never called from a request handler.** Boundaries are pre-fetched into
SQLite by ``scripts/ingest_geographies.py`` and served from there, so the
demo cannot be broken by an upstream outage.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.integrations.geo import BoundingBox

TIGERWEB_ROOT = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb"

#: Vintage-matched to the ACS release in app.integrations.census.variables.
TIGERWEB_SERVICE = "tigerWMS_ACS2024"

#: Layer 8 is "Census Tracts", confirmed against the service metadata.
TRACTS_LAYER_ID = 8

TIGERWEB_ORGANIZATION = "US Census Bureau"
TIGERWEB_DATASET = "TIGERweb Census Tracts (ACS 2024 vintage)"
TIGERWEB_LICENSE = "Public domain (US Government work)"

MARYLAND_STATE_FIPS = "24"
MONTGOMERY_COUNTY_FIPS = "031"


#: Study area for the MVP: downtown Silver Spring, covering the Fenton Village
#: commercial district.
#:
#: This box is a **project-defined study area, not an official boundary.**
#: Fenton Village is a commercial district with no GEOID and no published
#: Census geography, so some explicit rule is unavoidable. Stating it as a
#: reviewable constant is honest; silently hard-coding a tract list would not
#: be. The selection rule is "every tract whose area intersects this box",
#: which is deliberately inclusive - a tract partly covering the district
#: still describes people who walk through it.
#:
#: Anything derived from these tracts is an approximation of the district, and
#: must be presented as such.
FENTON_VILLAGE_STUDY_AREA = BoundingBox(
    min_lon=-77.040, min_lat=38.980, max_lon=-77.010, max_lat=39.005
)

STUDY_AREA_DESCRIPTION = (
    "Tracts intersecting a project-defined bounding box over downtown Silver "
    "Spring (lon -77.040 to -77.010, lat 38.980 to 39.005). Not an official "
    "Fenton Village boundary; the district has no Census geography."
)


class TigerWebError(RuntimeError):
    """A TIGERweb request failed or returned something unusable."""


class TigerWebClient:
    """Fetches tract boundaries as GeoJSON."""

    def __init__(
        self,
        *,
        service: str = TIGERWEB_SERVICE,
        layer_id: int = TRACTS_LAYER_ID,
        timeout: httpx.Timeout | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.service = service
        self.layer_id = layer_id
        self._timeout = timeout or httpx.Timeout(
            connect=10.0, read=90.0, write=10.0, pool=10.0
        )
        self._transport = transport

    @property
    def layer_url(self) -> str:
        """Citable URL of the layer these boundaries came from."""
        return f"{TIGERWEB_ROOT}/{self.service}/MapServer/{self.layer_id}"

    def fetch_tracts(
        self,
        bbox: BoundingBox,
        *,
        state_fips: str = MARYLAND_STATE_FIPS,
        county_fips: str = MONTGOMERY_COUNTY_FIPS,
    ) -> list[dict[str, Any]]:
        """Return GeoJSON features for tracts intersecting ``bbox``.

        Scoped by both the bounding box and a state/county filter, so a
        generous box can never pull in tracts from a neighbouring
        jurisdiction.
        """
        params = {
            "where": f"STATE='{state_fips}' AND COUNTY='{county_fips}'",
            "geometry": bbox.as_esri_envelope(),
            "geometryType": "esriGeometryEnvelope",
            "inSR": "4326",
            "outSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "GEOID,NAME,STATE,COUNTY,TRACT,BASENAME",
            "returnGeometry": "true",
            "f": "geojson",
        }

        try:
            with httpx.Client(
                timeout=self._timeout, transport=self._transport
            ) as client:
                response = client.get(f"{self.layer_url}/query", params=params)
        except httpx.TimeoutException as exc:
            raise TigerWebError(
                f"TIGERweb request timed out after {self._timeout.read}s"
            ) from exc
        except httpx.HTTPError as exc:
            raise TigerWebError(f"TIGERweb request failed: {exc}") from exc

        if response.status_code != 200:
            raise TigerWebError(
                f"TIGERweb returned HTTP {response.status_code}: "
                f"{response.text[:200]}"
            )

        try:
            payload: Any = response.json()
        except ValueError as exc:
            raise TigerWebError("TIGERweb returned non-JSON content") from exc

        # ArcGIS reports errors inside a 200 response, so status alone is not
        # enough to tell success from failure.
        if isinstance(payload, dict) and "error" in payload:
            raise TigerWebError(f"TIGERweb error: {payload['error']}")

        if not isinstance(payload, dict) or payload.get("type") != "FeatureCollection":
            raise TigerWebError("TIGERweb did not return a FeatureCollection")

        features = payload.get("features")
        if not isinstance(features, list):
            raise TigerWebError("TIGERweb FeatureCollection has no feature list")

        return [f for f in features if isinstance(f, dict)]
