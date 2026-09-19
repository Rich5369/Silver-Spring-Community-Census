"""Deterministic retrieval for parsed queries.

Each intent maps to a fixed set of stored metrics and a fixed answer
template. There is no query generation of any kind: the intent enum is
closed, so the set of database reads this module can perform is fixed at
import time.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.schemas.evidence import Evidence
from app.schemas.insights import InsightsResponse, SnapshotValue, ValueRange
from app.schemas.query import (
    SUGGESTED_QUESTIONS,
    Intent,
    ParsedQuery,
    QueryMap,
    QueryResponse,
)
from app.services import business_service
from app.services.geojson_service import build_business_features
from app.services.insights_service import build_insights
from app.services.trends_service import build_government_trends
from app.models import Facility
from app.schemas.facility import FacilityOut

UNSUPPORTED_ANSWER = (
    "This question is outside what the current dataset can answer. The data "
    "covers population, income, age, housing, commuting and mapped businesses "
    "for the Fenton Village study area."
)

NO_DATA_ANSWER = (
    "No data has been ingested yet, so this question cannot be answered. Run "
    "the ingestion scripts to populate the database."
)

STUDY_AREA_LIMITATION = (
    "Fenton Village is not a Census geography. Figures are aggregated from the "
    "Census tracts intersecting a bounding box over downtown Silver Spring and "
    "are approximations of the district, not published estimates for it."
)

BUSINESS_LIMITATION = (
    "Business records come from OpenStreetMap, which is volunteer-maintained. "
    "Coverage is good but not guaranteed complete, and a business absent from "
    "the map is not evidence that it does not exist."
)

MEDIAN_LIMITATION = (
    "A district-level median cannot be derived from tract-level medians, so a "
    "range across tracts is reported instead."
)

# Which stored metrics each intent reports.
_INTENT_METRICS: dict[Intent, tuple[str, ...]] = {
    Intent.COMMUNITY_OVERVIEW: (
        "total_population",
        "renter_share",
        "young_adult_share",
        "commute_active_share",
        "multilingual_household_share",
        "bachelors_or_higher_share",
    ),
    Intent.POPULATION: ("total_population", "young_adults_18_34", "young_adult_share"),
    Intent.INCOME: (),
    Intent.AGE: ("young_adults_18_34", "young_adult_share"),
    Intent.HOUSING: (
        "occupied_housing_units",
        "renter_occupied_households",
        "owner_occupied_households",
        "renter_share",
    ),
    # Only keys the community snapshot actually publishes. Per-mode counts
    # live in the tract metrics rather than the aggregated snapshot, so they
    # are reached through /api/v1/areas/{geoid}/metrics.
    Intent.COMMUTE: (
        "commuters_total",
        "commute_public_transport",
        "commute_transit_share",
        "commute_active_share",
        "worked_from_home_share",
    ),
    Intent.BUSINESS_CATEGORIES: (),
    Intent.NEARBY_BUSINESSES: (),
    Intent.BUSINESS_OPPORTUNITY: (
        "young_adult_share",
        "commute_active_share",
        "renter_share",
    ),
    Intent.DIVERSITY: ("multilingual_household_share", "bachelors_or_higher_share", "renter_share"),
    Intent.DISPLACEMENT: ("renter_share", "total_population"),
    Intent.GOVERNMENT_OVERVIEW: ("total_population", "renter_share", "young_adult_share", "multilingual_household_share"),
    Intent.TRENDS: (),
    Intent.POLICY_SUPPORT: ("total_population", "renter_share", "multilingual_household_share", "young_adult_share"),
    Intent.COMMUNITY_SUPPORT: ("renter_share", "multilingual_household_share", "commute_active_share"),
    Intent.BUSINESS_HEALTH: (),
    Intent.HEALTH_ACCESS: (),
    Intent.EDUCATION: ("bachelors_or_higher_share",),
    Intent.HOUSING_COSTS: ("rent_burdened_households", "rent_burden_share"),
    Intent.UNEMPLOYMENT: ("civilian_labor_force", "unemployed_people", "unemployment_rate"),
}

_INTENT_RANGES: dict[Intent, tuple[str, ...]] = {
    Intent.INCOME: ("median_household_income",),
    Intent.AGE: ("median_age",),
    Intent.COMMUNITY_OVERVIEW: ("median_household_income", "median_age"),
}


def _dedupe_evidence(items: list[Evidence]) -> list[Evidence]:
    """Collapse repeated citations, preserving order."""
    seen: set[tuple[str, str | None]] = set()
    unique: list[Evidence] = []
    for item in items:
        key = (item.dataset, item.source_variable)
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def _select(values: list[SnapshotValue], keys: tuple[str, ...]) -> list[SnapshotValue]:
    by_key = {value.key: value for value in values}
    return [by_key[key] for key in keys if key in by_key]


def _select_ranges(values: list[ValueRange], keys: tuple[str, ...]) -> list[ValueRange]:
    by_key = {value.key: value for value in values}
    return [by_key[key] for key in keys if key in by_key]


def _observation_text(insights: InsightsResponse, ids: tuple[str, ...]) -> list[str]:
    """Pull selected observation statements, in the order requested."""
    by_id = {observation.id: observation for observation in insights.observations}
    return [by_id[i].statement for i in ids if i in by_id]


_INTENT_OBSERVATIONS: dict[Intent, tuple[str, ...]] = {
    Intent.COMMUNITY_OVERVIEW: (
        "resident_population",
        "median_income_range",
        "renter_share",
        "young_adult_share",
        "commute_active_share",
        "largest_business_category",
    ),
    Intent.POPULATION: ("resident_population", "young_adult_share"),
    Intent.INCOME: ("median_income_range",),
    Intent.AGE: ("median_age_range", "young_adult_share"),
    Intent.HOUSING: ("renter_share",),
    Intent.COMMUTE: ("commute_active_share", "worked_from_home_share"),
    Intent.BUSINESS_CATEGORIES: (
        "largest_business_category",
        "business_category_spread",
    ),
    Intent.NEARBY_BUSINESSES: (),
    Intent.BUSINESS_OPPORTUNITY: (),
}


def _build_answer(intent: Intent, insights: InsightsResponse) -> str:
    """Assemble the answer from observation statements.

    Observations are themselves deterministic templates over stored values,
    so the answer contains no number the database does not hold.
    """
    statements = _observation_text(insights, _INTENT_OBSERVATIONS.get(intent, ()))
    if statements:
        return " ".join(statements)
    return NO_DATA_ANSWER


def _business_answer(category: str | None, count: int, total: int) -> str:
    """Deterministic sentence for a business lookup."""
    if category is None:
        if count == 0:
            return NO_DATA_ANSWER
        return f"{count} businesses are mapped in the study area."
    if count == 0:
        return (
            f"No businesses in the category '{category}' are mapped in the current "
            f"dataset, out of {total} mapped establishments. This reflects what is "
            "recorded in OpenStreetMap for the study area."
        )
    return (
        f"{count} of {total} mapped establishments in the study area are in the "
        f"category '{category}'."
    )


def _opportunity_answer(insights: InsightsResponse) -> str:
    """Describe observable market context without predicting success."""
    categories = insights.business_landscape.categories
    if not categories:
        return NO_DATA_ANSWER
    leaders = ", ".join(
        f"{item.category} ({item.count})" for item in categories[:3]
    )


def _civic_answer(intent: Intent, insights: InsightsResponse, trend_years: list[int]) -> str:
    if intent is Intent.TRENDS:
        if len(trend_years) < 2:
            return "Historical trend data is not available yet; ingest at least two ACS vintages to compare years."
        return f"The study area has comparable ACS vintages for {', '.join(map(str, trend_years))}. The response includes the observed population and renter-share series for those years."
    if intent is Intent.DISPLACEMENT:
        return "The data can show renter share, population, income ranges, and observed ACS change, but it cannot establish displacement or its causes. Review the indicators and evidence as signals requiring housing and permit data."
    if intent is Intent.DIVERSITY:
        return "The available community indicators describe language, education, age, and housing composition across the study-area tracts. They describe the population; they are not a complete measure of cultural identity or representation."
    if intent is Intent.BUSINESS_HEALTH:
        return "Business health cannot be measured from the current OSM snapshot: it has mapped locations and categories, but no opening dates, closures, vacancies, revenue, or survival records. Business-license and vacancy data are needed before claiming decline or failure."
    if intent is Intent.HEALTH_ACCESS:
        return "The current dataset does not contain hospital utilization, clinic capacity, mortality, or health-outcome data. ACS demographics can help identify populations for outreach, but cannot show that community health is declining or that hospital activity caused it."
    if intent is Intent.POLICY_SUPPORT:
        return "The platform can support policy scoping, not choose policy for officials. It shows who lives in the study area, housing and mobility context, observed change, and where evidence coverage is incomplete. Pair these signals with program, permit, and public-health data before implementing a policy."
    if intent is Intent.COMMUNITY_SUPPORT:
        return "The strongest current support signals are housing tenure, language, age, and mobility indicators. These can help target outreach and service design; they do not by themselves prove unmet need or determine funding."
    if intent is Intent.EDUCATION:
        return "The dataset reports the share of adults with a bachelor's degree or higher. It does not report school departures, dropout counts, graduation rates, or current enrollment, so those require school-district data."
    if intent is Intent.HOUSING_COSTS:
        return "The ACS reports renter households spending 35 percent or more of income on gross rent. This is a housing-cost pressure indicator, not a complete affordability or displacement finding."
    if intent is Intent.UNEMPLOYMENT:
        return "The ACS reports unemployment among the civilian labor force for the study-area tracts. It is a five-year survey estimate, not a monthly labor-market series."
    return "This civic summary combines population, housing, community composition, ACS change, and mapped-area context. Each reported value is returned with its source evidence."
    return (
        "The data cannot identify which business will be successful or recommend "
        "an opening. It can show current market context: the most represented "
        f"categories are {leaders} among "
        f"{insights.business_landscape.total_businesses} mapped businesses. "
        "Use these observed counts and the community indicators below to form "
        "a hypothesis, then validate it with local research."
    )


def unsupported_response(question: str) -> QueryResponse:
    """The answer when a question cannot be parsed."""
    return QueryResponse(
        question=question,
        understood=False,
        parsed=None,
        answer=UNSUPPORTED_ANSWER,
        suggestions=list(SUGGESTED_QUESTIONS),
        limitations=[STUDY_AREA_LIMITATION],
    )


def answer_query(session: Session, question: str, parsed: ParsedQuery) -> QueryResponse:
    """Retrieve the data for a validated query and build the response."""
    intent = parsed.intent
    insights = build_insights(session)

    limitations = [STUDY_AREA_LIMITATION]
    evidence: list[Evidence] = []
    metrics: list[SnapshotValue] = []
    ranges: list[ValueRange] = []
    categories = []
    businesses = []
    business_features = None
    trends = []
    facilities = []
    if intent in (Intent.TRENDS, Intent.DISPLACEMENT, Intent.GOVERNMENT_OVERVIEW):
        trend_response = build_government_trends(session)
        trends = trend_response.series
        limitations.extend(trend_response.limitations)

    if intent in (Intent.NEARBY_BUSINESSES, Intent.BUSINESS_CATEGORIES, Intent.BUSINESS_OPPORTUNITY):
        limitations.append(BUSINESS_LIMITATION)
    if intent in (Intent.INCOME, Intent.AGE, Intent.COMMUNITY_OVERVIEW, Intent.DIVERSITY):
        limitations.append(MEDIAN_LIMITATION)

    if intent is Intent.FACILITIES:
        requested_type = next((kind for kind in ("school", "church", "library", "park", "hospital", "clinic", "transit") if kind in question.lower()), None)
        query = session.query(Facility)
        if requested_type:
            query = query.filter(Facility.facility_type == requested_type)
        rows = query.order_by(Facility.name).all()
        facilities = [FacilityOut(id=row.id, name=row.name, facility_type=row.facility_type, latitude=row.latitude, longitude=row.longitude, address=row.address, source=f"{row.data_source.organization} ({row.external_id})", source_url=row.data_source.source_url) for row in rows]
        answer = f"{len(facilities)} {requested_type or 'civic facilities'} are mapped in the current OpenStreetMap snapshot. This is an inventory signal, not a complete official register."
        limitations.append("OpenStreetMap coverage may be incomplete; verify against the relevant county or state register.")
    elif intent in (Intent.TRENDS, Intent.DISPLACEMENT, Intent.DIVERSITY, Intent.GOVERNMENT_OVERVIEW, Intent.POLICY_SUPPORT, Intent.COMMUNITY_SUPPORT, Intent.BUSINESS_HEALTH, Intent.HEALTH_ACCESS, Intent.EDUCATION, Intent.HOUSING_COSTS, Intent.UNEMPLOYMENT):
        metrics = _select(insights.community_snapshot, _INTENT_METRICS[intent])
        answer = _civic_answer(intent, insights, sorted({point.year for series in trends for point in series.points}))
        for metric in metrics:
            evidence.extend(metric.evidence)
    elif intent is Intent.BUSINESS_OPPORTUNITY:
        categories = insights.business_landscape.categories
        answer = _opportunity_answer(insights)
        metrics = _select(insights.community_snapshot, _INTENT_METRICS[intent])
        evidence.extend(insights.business_landscape.evidence)
        for metric in metrics:
            evidence.extend(metric.evidence)
    elif intent is Intent.NEARBY_BUSINESSES:
        businesses = business_service.list_businesses(
            session, category=parsed.business_category
        )
        total = insights.business_landscape.total_businesses
        answer = _business_answer(parsed.business_category, len(businesses), total)
        evidence.extend(insights.business_landscape.evidence)
        all_features = build_business_features(session)
        wanted = {b.external_id for b in businesses}
        business_features = all_features.model_copy(
            update={
                "features": [f for f in all_features.features if f.id in wanted]
            }
        )
    elif intent is Intent.BUSINESS_CATEGORIES:
        categories = insights.business_landscape.categories
        answer = _build_answer(intent, insights)
        evidence.extend(insights.business_landscape.evidence)
    else:
        metrics = _select(insights.community_snapshot, _INTENT_METRICS.get(intent, ()))
        ranges = _select_ranges(insights.ranges, _INTENT_RANGES.get(intent, ()))
        answer = _build_answer(intent, insights)
        for metric in metrics:
            evidence.extend(metric.evidence)
            if not metric.available and metric.unavailable_reason:
                limitations.append(f"{metric.key}: {metric.unavailable_reason}")
        for value in ranges:
            evidence.extend(value.evidence)

    return QueryResponse(
        question=question,
        understood=True,
        parsed=parsed,
        answer=answer,
        metrics=metrics,
        ranges=ranges,
        categories=categories,
        businesses=businesses,
        trends=trends,
        facilities=facilities,
        map=QueryMap(
            area_geoids=insights.study_area.tract_geoids,
            businesses=business_features,
        ),
        evidence=_dedupe_evidence(evidence),
        limitations=limitations,
    )
