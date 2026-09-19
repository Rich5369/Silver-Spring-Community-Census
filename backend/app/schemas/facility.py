from __future__ import annotations
from pydantic import BaseModel, Field


class FacilityOut(BaseModel):
    id: int
    name: str
    facility_type: str
    latitude: float
    longitude: float
    address: str | None = None
    source: str
    source_url: str


class FacilityListResponse(BaseModel):
    count: int
    facilities: list[FacilityOut] = Field(default_factory=list)
