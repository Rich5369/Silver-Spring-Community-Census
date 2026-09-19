"""Constrained natural-language query route."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.schemas.query import QueryRequest, QueryResponse
from app.services.query_intent import parse_question
from app.services.query_service import answer_query, unsupported_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query", tags=["query"])


@router.post(
    "",
    response_model=QueryResponse,
    summary="Ask a constrained question about the study area",
)
def query(
    request: QueryRequest, session: Session = Depends(get_session)
) -> QueryResponse:
    """Answer a plain-language question from stored data.

    **This is not a chatbot.** A question is classified into one of eight
    intents, the intent selects a fixed set of database reads, and the answer
    is assembled by fixed templates from the values returned.

    * A language model, where one is configured, may only produce a
      `ParsedQuery` - an intent, a geography and an optional category. It
      cannot supply a statistic, and its output is rejected outright if it
      does not validate.
    * No SQL is generated. The intent enum is closed, so the set of possible
      database reads is fixed in code.
    * Parsing falls back to a deterministic keyword parser, which is what
      runs by default. The endpoint works with no external service available.

    Supported intents: `community_overview`, `population`, `income`, `age`,
    `housing`, `commute`, `business_categories`, `nearby_businesses`.

    A question outside those returns `understood: false` with
    `suggestions` listing questions that do work. Every response carries
    `evidence` for the values it reports and `limitations` describing what
    the figures can and cannot support.
    """
    parsed = parse_question(request.question)
    if parsed is None:
        return unsupported_response(request.question)

    try:
        return answer_query(session, request.question, parsed)
    except Exception:
        # Logged server-side with a traceback; the client is told nothing
        # about internal structure.
        logger.exception("Query failed for intent %s", parsed.intent)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The question could not be answered due to an internal error.",
        ) from None
