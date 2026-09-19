"""Geographic areas that metrics are reported for."""

from __future__ import annotations

from sqlalchemy import Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

# Values for Geography.geography_type. Plain strings rather than a SQL enum:
# SQLite has no native enum, and adding a type later should not need a
# migration during a hackathon.
GEOGRAPHY_TYPES: tuple[str, ...] = (
    "state",
    "county",
    "tract",
    "block_group",
    "neighborhood",
)


class Geography(Base):
    """An area a metric can be attached to.

    Covers both Census hierarchy levels and local areas of interest such as
    Fenton Village, which is a commercial district rather than a Census
    geography. Keeping both in one table lets a neighbourhood profile cite
    the tracts it was approximated from.
    """

    __tablename__ = "geographies"
    __table_args__ = (
        UniqueConstraint("geoid", name="uq_geographies_geoid"),
        Index("ix_geographies_type", "geography_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    #: Canonical identifier. The Census GEOID for Census geographies
    #: (e.g. "24031701700"), or a slug for local areas ("fenton-village").
    #: Unique, so re-ingestion updates the existing row.
    geoid: Mapped[str] = mapped_column(String(64), nullable=False)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    geography_type: Mapped[str] = mapped_column(String(32), nullable=False)

    # Census hierarchy components, null for non-Census areas. Stored as
    # zero-padded strings because FIPS codes have leading zeros.
    state_fips: Mapped[str | None] = mapped_column(String(2), nullable=True)
    county_fips: Mapped[str | None] = mapped_column(String(3), nullable=True)
    tract_code: Mapped[str | None] = mapped_column(String(6), nullable=True)
    block_group_code: Mapped[str | None] = mapped_column(String(1), nullable=True)

    #: Boundary as a serialised GeoJSON geometry. Text is the pragmatic
    #: choice for the SQLite MVP: no PostGIS, no SpatiaLite extension, and
    #: the frontend consumes GeoJSON directly. Point-in-polygon work is done
    #: in Python. Swapping to a real geometry column later is a migration,
    #: not a redesign.
    geometry_geojson: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<Geography geoid={self.geoid!r} type={self.geography_type!r}>"
