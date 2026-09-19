"""Build a small, defensible decision brief for local officials."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.schemas.government import CivicPriority
from app.services.insights_service import build_insights


def build_civic_priorities(session: Session) -> list[CivicPriority]:
    """Translate stored indicators into bounded planning questions.

    This intentionally does not score neighborhoods or claim causality. A
    priority is emitted only when the underlying metric is available, and the
    response tells officials what additional administrative data is needed.
    """
    insights = build_insights(session)
    values = {item.key: item for item in insights.community_snapshot}
    priorities: list[CivicPriority] = []

    rent = values.get("rent_burden_share")
    if rent and rent.available and rent.value is not None:
        priorities.append(CivicPriority(
            key="housing_pressure",
            priority="Housing pressure",
            signal=f"{rent.value:.1f}% of renter households are estimated to spend at least 35% of income on gross rent.",
            why_it_matters="Housing cost pressure can affect displacement risk, service stability, and the ability of residents to remain in the community.",
            next_step="Compare this signal with county eviction, rent, assessment, and code-enforcement records before targeting housing support.",
            evidence=rent.evidence,
            limitations=["ACS 5-year estimate; this is not an eviction or displacement count."],
        ))

    unemployment = values.get("unemployment_rate")
    if unemployment and unemployment.available and unemployment.value is not None:
        priorities.append(CivicPriority(
            key="labor_access",
            priority="Employment access",
            signal=f"The estimated unemployment rate is {unemployment.value:.1f}% among the civilian labor force.",
            why_it_matters="Employment conditions help officials assess whether outreach, workforce services, or transit access deserve closer review.",
            next_step="Disaggregate by tract and compare with workforce-program enrollment and transportation access; do not treat this as a monthly jobs report.",
            evidence=unemployment.evidence,
            limitations=["ACS 5-year estimate; it does not explain cause or identify individuals."],
        ))

    multilingual = values.get("multilingual_household_share")
    if multilingual and multilingual.available and multilingual.value is not None:
        priorities.append(CivicPriority(
            key="language_access",
            priority="Language access",
            signal=f"{multilingual.value:.1f}% of households are classified as multilingual in the stored ACS snapshot.",
            why_it_matters="Language composition is directly relevant to equitable notices, emergency communication, and public-meeting participation.",
            next_step="Use this as a screening signal for translated outreach, then validate with community organizations and county language-access standards.",
            evidence=multilingual.evidence,
            limitations=["The ACS category does not identify every language or measure preferred service language."],
        ))

    population = values.get("total_population")
    if population and population.available and population.value is not None:
        priorities.append(CivicPriority(
            key="service_capacity",
            priority="Service-capacity planning",
            signal=f"The study-area tract aggregation represents approximately {population.value:,.0f} residents.",
            why_it_matters="A common population baseline helps officials compare service coverage, facility access, and outreach demand across tracts.",
            next_step="Pair the population baseline with official facility capacity, 311 requests, and program participation before changing service levels.",
            evidence=population.evidence,
            limitations=["Fenton Village is not a Census geography; the total is an approximation across 14 tracts."],
        ))

    return priorities
