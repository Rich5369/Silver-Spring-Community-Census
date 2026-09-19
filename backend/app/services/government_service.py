"""Government-facing summaries built from the same stored facts as the app."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.schemas.government import GovernmentSummaryResponse
from app.services.insights_service import build_insights


def build_government_summary(session: Session) -> GovernmentSummaryResponse:
    """Return civic context without implying unsupported trends or causation."""
    return GovernmentSummaryResponse(
        study_area=build_insights(session),
        available_views=[
            "population and community composition",
            "housing tenure and renter share",
            "income and age ranges across tracts",
            "mapped business category mix",
            "tract coverage and source evidence",
        ],
        unavailable_views=[
            "historical trends",
            "income displacement",
            "year-over-year change",
            "causal explanations",
        ],
    )

