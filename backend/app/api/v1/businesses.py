"""Business routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.schemas.business import BusinessListResponse, CategoryListResponse
from app.services import business_service

router = APIRouter(prefix="/businesses", tags=["businesses"])


# Declared before any "/{id}" style route would be, so that "categories" is
# never captured as a path parameter.
@router.get(
    "/categories",
    response_model=CategoryListResponse,
    summary="Categories present, with counts",
)
def list_categories(session: Session = Depends(get_session)) -> CategoryListResponse:
    """Distinct business categories in the data, most common first.

    Built from stored rows, so every category returned has at least one
    business behind it. Use this to build filter controls that cannot produce
    an empty result.
    """
    return business_service.list_categories(session)


@router.get("", response_model=BusinessListResponse, summary="List businesses")
def list_businesses(
    session: Session = Depends(get_session),
    category: str | None = Query(
        default=None,
        description=(
            "Exact category match, e.g. 'Cafe'. Values come from "
            "GET /api/v1/businesses/categories. Matching is case-sensitive."
        ),
        examples=["Cafe"],
    ),
    q: str | None = Query(
        default=None, description="Case-insensitive substring search on name."
    ),
    limit: int | None = Query(default=None, ge=1, le=1000),
) -> BusinessListResponse:
    """Businesses ingested from OpenStreetMap around Fenton Village.

    Served from the database; Overpass is queried only during ingestion, so a
    page load never depends on upstream availability.

    An unknown category is not an error - it returns an empty list, which is
    a valid answer to "show me bakeries" when there are none.
    """
    businesses = business_service.list_businesses(
        session, category=category, query=q, limit=limit
    )
    return BusinessListResponse(businesses=businesses)
