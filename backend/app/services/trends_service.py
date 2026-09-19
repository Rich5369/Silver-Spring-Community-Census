from __future__ import annotations

from collections import defaultdict

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.integrations.census.variables import METRIC_SPECS_BY_KEY
from app.models import CommunityMetric, DataSource, Geography
from app.schemas.trends import (
    GovernmentTrendsResponse,
    TrendPoint,
    TrendSeries,
    TrendSource,
)
from app.services.insights_service import build_insights

_SUMMABLE_KEYS = (
    "total_population",
    "renter_occupied_households",
    "occupied_housing_units",
)

#: Medians are not additive, so this one is reported as a range across tracts.
_INCOME_KEY = "median_household_income"

_INCOME_METHOD = (
    "Median household income is reported as the range across the study-area "
    "tracts. A district-level median cannot be derived from tract medians: "
    "medians are not additive, and averaging them would produce a number the "
    "source data does not support."
)


def _source_for(session: Session, metric_key: str, years: list[int]) -> TrendSource | None:
    """Assemble provenance for a series from the releases actually behind it."""
    if not years:
        return None
    releases = (
        session.query(DataSource)
        .join(CommunityMetric, CommunityMetric.data_source_id == DataSource.id)
        .filter(CommunityMetric.metric_key == metric_key)
        .filter(DataSource.dataset_year.in_(years))
        .distinct()
        .order_by(DataSource.dataset_year)
        .all()
    )
    if not releases:
        return None
    spec = METRIC_SPECS_BY_KEY.get(metric_key)
    newest = releases[-1]
    return TrendSource(
        organization=newest.organization,
        # The per-year dataset strings differ only by the year in parentheses,
        # which ``years`` already carries, so the family name is used here.
        dataset="American Community Survey 5-Year Estimates",
        table=spec.source_variable if spec else metric_key,
        urls=[release.source_url for release in releases],
        years=[int(release.dataset_year) for release in releases],
    )


def build_government_trends(session: Session) -> GovernmentTrendsResponse:
    """Aggregate comparable ACS vintages for the 14-tract study area."""
    geoids = build_insights(session).study_area.tract_geoids
    base = session.query(
        DataSource.dataset_year, CommunityMetric.metric_key,
        func.sum(CommunityMetric.value),
    ).join(DataSource, CommunityMetric.data_source_id == DataSource.id)
    base = base.join(Geography, CommunityMetric.geography_id == Geography.id)
    base = base.filter(Geography.geoid.in_(geoids), DataSource.dataset_year.isnot(None))
    rows = base.filter(CommunityMetric.metric_key.in_(_SUMMABLE_KEYS))
    rows = rows.group_by(DataSource.dataset_year, CommunityMetric.metric_key).all()
    values = defaultdict(dict)
    for year, key, value in rows:
        values[int(year)][key] = float(value or 0)
    years = sorted(values)
    population = [TrendPoint(year=y, value=values[y]["total_population"]) for y in years if "total_population" in values[y]]
    renter = [
        TrendPoint(year=y, value=values[y]["renter_occupied_households"] / values[y]["occupied_housing_units"] * 100)
        for y in years if values[y].get("occupied_housing_units")
    ]

    income_rows = session.query(
        DataSource.dataset_year,
        func.min(CommunityMetric.value),
        func.max(CommunityMetric.value),
        func.count(CommunityMetric.id),
    ).join(DataSource, CommunityMetric.data_source_id == DataSource.id)
    income_rows = income_rows.join(Geography, CommunityMetric.geography_id == Geography.id)
    income_rows = income_rows.filter(
        Geography.geoid.in_(geoids),
        DataSource.dataset_year.isnot(None),
        CommunityMetric.metric_key == _INCOME_KEY,
        CommunityMetric.value.isnot(None),
    )
    income_rows = income_rows.group_by(DataSource.dataset_year).order_by(DataSource.dataset_year).all()
    income = [
        TrendPoint(year=int(year), low=float(low), high=float(high))
        for year, low, high, count in income_rows
        if count
    ]
    income_tracts = max((count for *_, count in income_rows), default=0)
    income_source = _source_for(session, _INCOME_KEY, [point.year for point in income])
    if income_source is not None:
        income_source.tract_count = int(income_tracts)

    population_source = _source_for(session, "total_population", [p.year for p in population])
    renter_source = _source_for(session, "renter_occupied_households", years)
    for aggregated in (population_source, renter_source):
        if aggregated is not None:
            aggregated.tract_count = len(geoids)

    return GovernmentTrendsResponse(
        years=sorted({*years, *(point.year for point in income)}),
        series=[
            TrendSeries(
                key="total_population", label="Population", unit="people",
                basis="total", points=population, source=population_source,
                method=f"Sum of total_population across {len(geoids)} study-area tracts.",
            ),
            TrendSeries(
                key="renter_share", label="Renter-occupied share", unit="percent",
                basis="total", points=renter,
                source=renter_source,
            ),
            TrendSeries(
                key=_INCOME_KEY, label="Median household income", unit="usd",
                basis="range", points=income, source=income_source,
                method=_INCOME_METHOD,
            ),
        ],
        limitations=[
            "These are aggregated ACS tract estimates, not an official Fenton Village estimate.",
            "Changes describe the observed vintages and do not establish causation or displacement.",
            "Median household income is a range across tracts, not a single district median.",
        ],
    )
