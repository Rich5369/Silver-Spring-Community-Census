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
    Intent.POPULATION: ("total_population", "young_adults_20_34", "young_adult_share"),
    Intent.INCOME: (),
    Intent.AGE: ("young_adults_20_34", "young_adult_share"),
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
        "commute_active_share",
        "worked_from_home_share",
    ),
    Intent.BUSINESS_CATEGORIES: (),
    Intent.NEARBY_BUSINESSES: (),
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

    if intent in (Intent.NEARBY_BUSINESSES, Intent.BUSINESS_CATEGORIES):
        limitations.append(BUSINESS_LIMITATION)
    if intent in (Intent.INCOME, Intent.AGE, Intent.COMMUNITY_OVERVIEW):
        limitations.append(MEDIAN_LIMITATION)

    if intent is Intent.NEARBY_BUSINESSES:
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
        map=QueryMap(
            area_geoids=insights.study_area.tract_geoids,
            businesses=business_features,
        ),
        evidence=_dedupe_evidence(evidence),
        limitations=limitations,
    )
