"""Business response schemas.

The envelope matches the contract the frontend already wrote in
``src/services/api.js`` and the root README: ``{"businesses": [...]}`` with
``id``, ``name``, ``category``, ``latitude``, ``longitude``, ``address`` and
``source``.

Extra evidence fields are added alongside them. The frontend's
``normalizeBusinesses`` adapter copies only the fields it knows and ignores
the rest, so this is a superset: it works unchanged today, and can surface
richer provenance later without a backend change.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class BusinessOut(BaseModel):
    """One mappable business."""

    id: int
    name: str
    category: str
    latitude: float
    longitude: float
    address: str | None = None
    #: Human-readable attribution, e.g. "OpenStreetMap contributors (node/1)".
    source: str

    # --- Evidence extras, ignored by the current frontend adapter ----------
    source_url: str
    #: The upstream element id, e.g. "node/1234567".
    external_id: str
    #: The OSM tag that determined the category, e.g. "amenity=cafe". Lets a
    #: surprising classification be traced without a database query.
    source_tag: str | None = None
    dataset: str


class BusinessListResponse(BaseModel):
    """The envelope the frontend expects."""

    businesses: list[BusinessOut] = Field(default_factory=list)
