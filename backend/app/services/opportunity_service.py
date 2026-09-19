"""Build transparent market context from stored facts, never a score."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.schemas.opportunity import OpportunityIndicator, OpportunityResponse
from app.services import business_service
from app.services.insights_service import build_insights


LIMITATIONS = [
    "These indicators describe the study area; they are not a prediction of business success.",
    "Fenton Village is approximated by a project-defined set of Census tracts, not an official Census geography.",
    "Business records come from volunteer-maintained OpenStreetMap and may be incomplete.",
]


def build_opportunity_context(session: Session, category: str) -> OpportunityResponse:
    insights = build_insights(session)
    businesses = business_service.list_businesses(session, category=category)
    wanted = {"young_adult_share", "commute_active_share", "renter_share"}
    indicators = [
        OpportunityIndicator(
            key=value.key,
            label=value.label,
            value=value.value,
            unit=value.unit,
            evidence=value.evidence,
        )
        for value in insights.community_snapshot
        if value.key in wanted
    ]
    evidence = list(insights.business_landscape.evidence)
    for indicator in indicators:
        evidence.extend(indicator.evidence)
    return OpportunityResponse(
        category=category,
        competition_count=len(businesses),
        total_businesses=insights.business_landscape.total_businesses,
        indicators=indicators,
        evidence=evidence,
        limitations=LIMITATIONS,
    )
