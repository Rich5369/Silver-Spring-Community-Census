"""Geography boundary routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.schemas.geojson import FeatureCollection
from app.services.geojson_service import build_feature_collection

router = APIRouter(tags=["geography"])


@router.get(
    "/geographies",
    response_model=FeatureCollection,
    summary="Census tract boundaries with community metrics",
)
def geographies(session: Session = Depends(get_session)) -> FeatureCollection:
    """Return study-area tracts as a GeoJSON FeatureCollection.

    Served entirely from the database. Each feature carries a stable ``GEOID``
    as both its ``id`` and ``properties.geoid``, its metrics, and the
    provenance for both the metrics and the boundary.
    """
    return build_feature_collection(session)
