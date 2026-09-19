"""Business listing routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.models import Business
from app.repositories import BusinessRepository
from app.schemas.business import BusinessListResponse, BusinessOut

router = APIRouter(tags=["businesses"])


def _to_schema(business: Business) -> BusinessOut:
    return BusinessOut(
        id=business.id,
        name=business.name,
        category=business.category,
        latitude=business.latitude,
        longitude=business.longitude,
        address=business.address,
        source=business.source,
        source_url=business.source_url,
        external_id=business.external_id,
        source_tag=business.source_tag,
        dataset=business.data_source.dataset,
    )


@router.get(
    "/businesses",
    response_model=BusinessListResponse,
    summary="Businesses around Fenton Village",
)
def businesses(
    session: Session = Depends(get_session),
    category: str | None = Query(
        default=None,
        description="Exact category match, e.g. 'Cafe'. Omit for all.",
    ),
    q: str | None = Query(default=None, description="Case-insensitive name search."),
    limit: int | None = Query(default=None, ge=1, le=1000),
) -> BusinessListResponse:
    """List businesses ingested from OpenStreetMap.

    Served from the database. Overpass is queried only by
    ``scripts/ingest_businesses.py``, never while handling a request, so a
    page load cannot be blocked by upstream rate limits.

    Filtering is available here, but the frontend currently filters
    client-side over the full list; both work, and neither needs the other
    to change.
    """
    results = BusinessRepository(session).search(category=category, query=q, limit=limit)
    return BusinessListResponse(businesses=[_to_schema(b) for b in results])
