"""Combined map payload schema."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.geojson import FeatureCollection


class CommunityMapResponse(BaseModel):
    """Everything needed to draw the community map in one request.

    Two standard GeoJSON FeatureCollections, so each can be handed straight
    to ``L.geoJSON`` without reshaping:

    * ``areas`` - tract polygons, each carrying its metrics and evidence.
    * ``businesses`` - business points, each carrying its attribution.

    A wrapper rather than one FeatureCollection because the two layers are
    drawn differently (choropleth vs markers) and mixing polygons and points
    in one collection would force the client to partition them again.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "areas": {"type": "FeatureCollection", "features": []},
                "businesses": {"type": "FeatureCollection", "features": []},
                "area_count": 14,
                "business_count": 207,
            }
        }
    )

    areas: FeatureCollection = Field(description="Tract polygons with metrics.")
    businesses: FeatureCollection = Field(description="Business points.")
    area_count: int
    business_count: int
