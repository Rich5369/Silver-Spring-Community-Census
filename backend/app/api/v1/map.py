"""Combined map payload route."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.schemas.map import CommunityMapResponse
from app.services.geojson_service import build_community_map

router = APIRouter(prefix="/map", tags=["map"])


@router.get(
    "/community",
    response_model=CommunityMapResponse,
    summary="Everything needed to draw the community map",
)
def community_map(session: Session = Depends(get_session)) -> CommunityMapResponse:
    """Both map layers in one request.

    Returns two standard GeoJSON FeatureCollections, each usable directly
    with ``L.geoJSON``:

    * ``areas`` - tract Polygons, each carrying its metrics and evidence.
    * ``businesses`` - business Points, each carrying its attribution.

    Positions are ``[longitude, latitude]`` per RFC 7946, which is the
    reverse of Leaflet's ``[lat, lng]``. ``L.geoJSON`` handles the
    conversion; constructing markers by hand does not.
    """
    return build_community_map(session)
