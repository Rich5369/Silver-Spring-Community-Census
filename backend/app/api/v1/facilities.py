from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.models import Facility
from app.schemas.facility import FacilityListResponse, FacilityOut

router = APIRouter(prefix="/facilities", tags=["facilities"])


@router.get("", response_model=FacilityListResponse)
def list_facilities(
    facility_type: str | None = Query(default=None, alias="type"),
    session: Session = Depends(get_session),
) -> FacilityListResponse:
    query = session.query(Facility).order_by(Facility.facility_type, Facility.name)
    if facility_type:
        query = query.filter(Facility.facility_type == facility_type.lower())
    rows = query.all()
    return FacilityListResponse(
        count=len(rows),
        facilities=[FacilityOut(
            id=row.id, name=row.name, facility_type=row.facility_type,
            latitude=row.latitude, longitude=row.longitude, address=row.address,
            source=f"{row.data_source.organization} ({row.external_id})",
            source_url=row.data_source.source_url,
        ) for row in rows],
    )
