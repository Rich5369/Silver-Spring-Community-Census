"""Deterministic insight routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.schemas.insights import InsightsResponse
from app.services.insights_service import build_insights

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get(
    "/fenton-village",
    response_model=InsightsResponse,
    summary="Deterministic summary of the Fenton Village study area",
)
def fenton_village_insights(
    session: Session = Depends(get_session),
) -> InsightsResponse:
    """Summarise the stored data for a local business owner.

    Everything here is arithmetic over stored values - given the same
    database, the response is always identical. There is no model and no
    heuristic involved.

    **What this does not do**

    * It makes no recommendations. Statements describe the dataset; deciding
      what to do about it is the reader's job.
    * It asserts no causation. Two figures appearing together is not a claim
      that one explains the other.
    * It invents nothing. A figure the data cannot support is reported in
      `unavailable` with the reason, never estimated.

    **Structure**

    * `study_area` - what "Fenton Village" means here, and why the figures
      are approximations.
    * `community_snapshot` - source values, each with its derivation,
      coverage and evidence.
    * `ranges` - non-additive metrics such as medians, reported as a spread
      across tracts.
    * `business_landscape` - category counts over mapped businesses.
    * `observations` - factual statements, kept separate from the source data
      they are computed from.
    * `unavailable` - what is deliberately not reported, and why.

    Note that a district-level **median** income or age is listed as
    unavailable: medians are not additive, so averaging tract medians would
    produce a number the source data does not support.
    """
    return build_insights(session)
