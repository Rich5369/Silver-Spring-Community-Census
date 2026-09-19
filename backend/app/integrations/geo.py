"""Shared geographic primitives."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BoundingBox:
    """A WGS84 lon/lat envelope."""

    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float

    def as_esri_envelope(self) -> str:
        """``xmin,ymin,xmax,ymax`` - the ArcGIS envelope order."""
        return f"{self.min_lon},{self.min_lat},{self.max_lon},{self.max_lat}"

    def as_overpass_bbox(self) -> str:
        """``south,west,north,east`` - the Overpass order.

        Deliberately a different method from :meth:`as_esri_envelope`:
        the two services order their bounds differently, and silently
        swapping them yields an empty result set rather than an error.
        """
        return f"{self.min_lat},{self.min_lon},{self.max_lat},{self.max_lon}"

    def contains(self, *, lon: float, lat: float) -> bool:
        """Whether a point falls inside this box."""
        return self.min_lon <= lon <= self.max_lon and self.min_lat <= lat <= self.max_lat
