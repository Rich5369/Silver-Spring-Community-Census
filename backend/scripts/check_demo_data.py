"""Fail fast if a deployed demo database is empty or incomplete."""

from __future__ import annotations

from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.models import Business, CommunityMetric, Geography


def main() -> None:
    with SessionLocal() as session:
        area_count = session.scalar(
            select(func.count()).select_from(Geography).where(Geography.geometry_geojson.is_not(None))
        ) or 0
        business_count = session.scalar(select(func.count()).select_from(Business)) or 0
        metric_count = session.scalar(select(func.count()).select_from(CommunityMetric)) or 0

    print({"area_count": area_count, "business_count": business_count, "metric_count": metric_count})
    if area_count != 14 or business_count != 207 or metric_count == 0:
        raise SystemExit("demo database verification failed")


if __name__ == "__main__":
    main()
