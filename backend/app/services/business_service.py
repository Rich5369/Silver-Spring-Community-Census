"""Business query logic."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Business
from app.repositories import BusinessRepository
from app.schemas.business import (
    BusinessOut,
    CategoryCount,
    CategoryListResponse,
)


def to_business(business: Business) -> BusinessOut:
    """Map a business row to its response schema, attribution included."""
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


def list_businesses(
    session: Session,
    *,
    category: str | None = None,
    query: str | None = None,
    limit: int | None = None,
) -> list[BusinessOut]:
    """Businesses filtered by category and/or name."""
    return [
        to_business(business)
        for business in BusinessRepository(session).search(
            category=category, query=query, limit=limit
        )
    ]


def list_categories(session: Session) -> CategoryListResponse:
    """Categories present in the data, with counts."""
    counts = [
        CategoryCount(category=category, count=count)
        for category, count in BusinessRepository(session).category_counts()
    ]
    return CategoryListResponse(count=len(counts), categories=counts)
