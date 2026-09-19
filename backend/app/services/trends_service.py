from __future__ import annotations

from collections import defaultdict

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import CommunityMetric, DataSource, Geography
from app.schemas.trends import GovernmentTrendsResponse, TrendPoint, TrendSeries
from app.services.insights_service import build_insights


def build_government_trends(session: Session) -> GovernmentTrendsResponse:
    """Aggregate comparable ACS vintages for the 14-trัก study area."""
    geoids = build_insights(session).study_area.tract_geoids
    rows = session.query(
        DataSource.dataset_year, CommunityMetric.metric_key,
        func.sum(CommunityMetric.value),
    ).join(DataSource, CommunityMetric.data_source_id == DataSource.id)
    rows = rows.join(Geography, CommunityMetric.geography_id == Geography.id)
    rows = rows.filter(Geography.geoid.in_(geoids), DataSource.dataset_year.isnot(None))
    rows = rows.filter(CommunityMetric.metric_key.in_(("total_population", "renter_occupied_households", "occupied_housing_units")))
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
    return GovernmentTrendsResponse(
        years=years,
        series=[
            TrendSeries(key="total_population", label="Population", unit="people", points=population),
            TrendSeries(key="renter_share", label="Renter-occupied share", unit="percent", points=renter),
        ],
        limitations=[
            "These are aggregated ACS tract estimates, not an official Fenton Village estimate.",
            "Changes describe the observed vintages and do not establish causation or displacement.",
        ],
    )
