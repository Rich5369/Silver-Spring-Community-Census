"""Area and metric routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.models.geography import GEOGRAPHY_TYPES
from app.schemas.area import AreaListResponse, AreaMetricsResponse, AreaOut
from app.schemas.evidence import ErrorResponse
from app.services import area_service

router = APIRouter(prefix="/areas", tags=["areas"])

NOT_FOUND = {status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Unknown GEOID"}}

GeoidPath = Path(
    description="Census GEOID, e.g. '24031701701' for a tract or '24031' for a county.",
    examples=["24031701701"],
)


@router.get("", response_model=AreaListResponse, summary="List geographic areas")
def list_areas(
    session: Session = Depends(get_session),
    geography_type: str | None = Query(
        default=None,
        description=f"Filter by type. One of: {', '.join(GEOGRAPHY_TYPES)}.",
        examples=["tract"],
    ),
    with_boundary_only: bool = Query(
        default=False,
        description=(
            "Return only areas that have a stored GeoJSON boundary. These are "
            "the Silver Spring study-area tracts that can be drawn on the map."
        ),
    ),
    limit: int | None = Query(default=None, ge=1, le=1000),
) -> AreaListResponse:
    """List areas that have been ingested.

    Ingestion covers Montgomery County and all of its tracts, so this returns
    a few hundred rows by default. Pass ``with_boundary_only=true`` for the
    14 study-area tracts that have map geometry.
    """
    areas = area_service.list_areas(
        session,
        geography_type=geography_type,
        with_boundary_only=with_boundary_only,
        limit=limit,
    )
    return AreaListResponse(count=len(areas), areas=areas)


@router.get(
    "/{geoid}",
    response_model=AreaOut,
    responses=NOT_FOUND,
    summary="Get one area by GEOID",
)
def get_area(
    geoid: str = GeoidPath, session: Session = Depends(get_session)
) -> AreaOut:
    """Fetch a single area. Returns 404 if the GEOID has not been ingested."""
    area = area_service.get_area(session, geoid)
    if area is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No area found with GEOID {geoid!r}.",
        )
    return area


@router.get(
    "/{geoid}/metrics",
    response_model=AreaMetricsResponse,
    responses=NOT_FOUND,
    summary="Community metrics for one area",
)
def get_area_metrics(
    geoid: str = GeoidPath, session: Session = Depends(get_session)
) -> AreaMetricsResponse:
    """Every metric recorded for an area, each with its evidence.

    A metric's ``value`` may be ``null`` where the Census suppressed the
    estimate. Null means "not available" - never zero.

    An area that exists but has no metrics returns 200 with an empty list;
    only an unknown GEOID is a 404.
    """
    result = area_service.get_area_metrics(session, geoid)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No area found with GEOID {geoid!r}.",
        )
    return result
