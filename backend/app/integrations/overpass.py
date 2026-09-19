"""OpenStreetMap business POIs via the Overpass API.

Scope is one small bounding box around Fenton Village - this is an MVP
ingestion, not an OSM crawler.

**Never called from a request handler.** Overpass is free, shared, volunteer-
run infrastructure that rate-limits and occasionally goes down. Hitting it
per page view would be both rude and fragile, so POIs are fetched once into
SQLite by ``scripts/ingest_businesses.py`` and served from there.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.integrations.geo import BoundingBox
from app.integrations.osm_categories import classify, is_business

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

OSM_ORGANIZATION = "OpenStreetMap contributors"
OSM_DATASET = "OpenStreetMap POIs via Overpass API"
OSM_LICENSE = "Open Database License (ODbL) 1.0"
OSM_ATTRIBUTION_URL = "https://www.openstreetmap.org/copyright"

#: The Fenton Village commercial district: the Fenton Street corridor and the
#: blocks around it. Tighter than the Census study area in
#: ``app.integrations.tigerweb`` because this is the walkable retail district
#: a business owner competes in, not the tracts whose residents shop there.
FENTON_VILLAGE_BBOX = BoundingBox(
    min_lon=-77.0320, min_lat=38.9875, max_lon=-77.0170, max_lat=38.9985
)


class OverpassError(RuntimeError):
    """An Overpass request failed or returned something unusable."""


@dataclass(frozen=True)
class OsmPlace:
    """A normalised business POI from OSM."""

    osm_id: str
    name: str
    category: str
    latitude: float
    longitude: float
    address: str | None
    #: The ``key=value`` tag that drove classification, for debugging.
    source_tag: str | None
    #: The POI's business-relevant original tags, kept as evidence.
    tags: dict[str, str]


def build_query(bbox: BoundingBox, timeout_seconds: int = 60) -> str:
    """Build the Overpass QL query for business POIs in ``bbox``.

    ``nwr`` covers nodes, ways and relations in one pass, and ``out center``
    gives ways and relations a single representative coordinate so every
    result can be mapped as a point.
    """
    box = bbox.as_overpass_bbox()
    clauses = "\n  ".join(f'nwr["{key}"]({box});' for key in ("shop", "amenity", "craft", "healthcare", "office"))
    return f"[out:json][timeout:{timeout_seconds}];\n(\n  {clauses}\n);\nout center tags;"


def _compose_address(tags: dict[str, str]) -> str | None:
    """Build a readable address from ``addr:*`` tags.

    Most OSM POIs carry some address tags and few carry all of them, so each
    part is optional and a POI with none yields ``None`` rather than a string
    of stray commas.
    """
    house = tags.get("addr:housenumber", "").strip()
    street = tags.get("addr:street", "").strip()
    city = tags.get("addr:city", "").strip()
    state = tags.get("addr:state", "").strip()
    postcode = tags.get("addr:postcode", "").strip()

    line = " ".join(part for part in (house, street) if part)
    locality = ", ".join(part for part in (city, state) if part)
    if postcode:
        locality = f"{locality} {postcode}".strip()

    full = ", ".join(part for part in (line, locality) if part)
    return full or None


def _coordinates(element: dict[str, Any]) -> tuple[float, float] | None:
    """Extract lat/lon from a node, or a way/relation's computed centre."""
    lat, lon = element.get("lat"), element.get("lon")
    if lat is None or lon is None:
        centre = element.get("center")
        if isinstance(centre, dict):
            lat, lon = centre.get("lat"), centre.get("lon")
    try:
        return float(lat), float(lon)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def normalize_element(element: dict[str, Any]) -> OsmPlace | None:
    """Convert one Overpass element to an :class:`OsmPlace`.

    Returns ``None`` when the element is unusable - no name, no usable
    coordinates, or not a business. Skipping is deliberate: an unnamed POI
    renders as a blank marker a user cannot act on.
    """
    if not isinstance(element, dict):
        return None

    tags = element.get("tags")
    if not isinstance(tags, dict):
        return None
    tags = {str(k): str(v) for k, v in tags.items()}

    name = tags.get("name", "").strip()
    if not name or not is_business(tags):
        return None

    coordinates = _coordinates(element)
    if coordinates is None:
        return None
    latitude, longitude = coordinates
    if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
        return None

    element_type = str(element.get("type", "")).strip()
    element_id = element.get("id")
    if not element_type or element_id is None:
        return None

    category, source_tag = classify(tags)

    # Keep only business-relevant tags rather than the whole blob: enough to
    # audit a classification, without storing opening hours and wheelchair
    # access for 200 POIs.
    kept = {
        key: value
        for key, value in tags.items()
        if key in {"shop", "amenity", "craft", "healthcare", "office", "cuisine", "brand"}
    }

    return OsmPlace(
        osm_id=f"{element_type}/{element_id}",
        name=name,
        category=category,
        latitude=latitude,
        longitude=longitude,
        address=_compose_address(tags),
        source_tag=source_tag,
        tags=kept,
    )


class OverpassClient:
    """Fetches business POIs from the Overpass API."""

    def __init__(
        self,
        *,
        url: str = OVERPASS_URL,
        timeout: httpx.Timeout | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.url = url
        # Overpass queues requests under load, so the read timeout is long
        # while the connect timeout stays short.
        self._timeout = timeout or httpx.Timeout(
            connect=10.0, read=180.0, write=10.0, pool=10.0
        )
        self._transport = transport

    def fetch_places(self, bbox: BoundingBox) -> list[OsmPlace]:
        """Fetch and normalise business POIs within ``bbox``."""
        query = build_query(bbox)

        try:
            with httpx.Client(
                timeout=self._timeout, transport=self._transport
            ) as client:
                # POST: Overpass prefers it for queries and it avoids URL
                # length limits as the tag list grows.
                response = client.post(
                    self.url,
                    data={"data": query},
                    headers={"User-Agent": "SilverSpringCommunityCensus/0.1 (hackathon MVP)"},
                )
        except httpx.TimeoutException as exc:
            raise OverpassError(
                f"Overpass request timed out after {self._timeout.read}s"
            ) from exc
        except httpx.HTTPError as exc:
            raise OverpassError(f"Overpass request failed: {exc}") from exc

        if response.status_code == 429:
            raise OverpassError(
                "Overpass rate limit reached (HTTP 429). Wait and retry; "
                "this is shared public infrastructure."
            )
        if response.status_code == 504:
            raise OverpassError(
                "Overpass gateway timeout (HTTP 504). Try a smaller bounding box."
            )
        if response.status_code != 200:
            raise OverpassError(
                f"Overpass returned HTTP {response.status_code}: "
                f"{response.text[:200]}"
            )

        try:
            payload: Any = response.json()
        except ValueError as exc:
            raise OverpassError("Overpass returned non-JSON content") from exc

        if not isinstance(payload, dict):
            raise OverpassError("Overpass returned an unexpected payload shape")

        elements = payload.get("elements")
        if not isinstance(elements, list):
            raise OverpassError("Overpass payload contained no element list")

        places = [
            place
            for element in elements
            if (place := normalize_element(element)) is not None
        ]

        # Ways and relations can duplicate a node for the same establishment.
        # Keep the first occurrence of each OSM id.
        unique: dict[str, OsmPlace] = {}
        for place in places:
            unique.setdefault(place.osm_id, place)
        return list(unique.values())

    def fetch_facilities(self, bbox: BoundingBox) -> list[OsmPlace]:
        """Fetch named civic facilities without mixing them into businesses."""
        box = bbox.as_overpass_bbox()
        query = f'''[out:json][timeout:60];(
          nwr["amenity"~"school|library|hospital|clinic|place_of_worship|social_centre|community_centre|kindergarten|bus_station|social_facility"]({box});
          nwr["leisure"~"park|playground"]({box});
        );out center tags;'''
        try:
            with httpx.Client(timeout=self._timeout, transport=self._transport) as client:
                response = client.post(self.url, data={"data": query}, headers={"User-Agent": "SilverSpringCommunityCensus/0.1"})
                response.raise_for_status()
                elements = response.json().get("elements", [])
        except (httpx.HTTPError, ValueError) as exc:
            raise OverpassError(f"Overpass facility request failed: {exc}") from exc
        result = []
        seen = set()
        types = {"school": "school", "kindergarten": "school", "library": "library", "hospital": "hospital", "clinic": "clinic", "place_of_worship": "church", "park": "park", "playground": "park", "bus_station": "transit", "social_centre": "community", "community_centre": "community", "social_facility": "community"}
        for element in elements:
            tags = element.get("tags", {})
            name = str(tags.get("name", "")).strip()
            coordinates = _coordinates(element)
            raw_type = tags.get("amenity") or tags.get("leisure")
            facility_type = types.get(raw_type)
            key = f"{element.get('type')}/{element.get('id')}"
            if name and coordinates and facility_type and key not in seen:
                seen.add(key)
                result.append(OsmPlace(key, name, facility_type, coordinates[0], coordinates[1], _compose_address(tags), raw_type, {}))
        return result
