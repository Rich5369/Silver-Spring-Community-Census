from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.schemas.trends import GovernmentTrendsResponse
from app.services.trends_service import build_government_trends

router = APIRouter(prefix="/government", tags=["government"])


@router.get("/trends", response_model=GovernmentTrendsResponse)
def government_trends(session: Session = Depends(get_session)) -> GovernmentTrendsResponse:
    return build_government_trends(session)

