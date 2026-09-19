"""Tests for the constrained query endpoint.

No external language model is involved anywhere. Classifier behaviour is
exercised with local fakes, and the default path is the deterministic keyword
parser.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.schemas.query import SUGGESTED_QUESTIONS, Intent, ParsedQuery
from app.services.query_intent import (
    parse_question,
    rule_based_parse,
    validate_classifier_output,
)
from tests.test_insights import _seed_area, _seed_businesses, TRACT_A, TRACT_B

ENDPOINT = "/api/v1/query"


def _seed(session: Session) -> None:
    _seed_area(session, {"24031000100": TRACT_A, "24031000200": TRACT_B})
    _seed_businesses(session, ["Cafe"] * 3 + ["Restaurant"] * 5 + ["Retail"] * 2)


def _ask(client: TestClient, question: str) -> dict:
    response = client.post(ENDPOINT, json={"question": question})
    assert response.status_code == 200, response.text
    return response.json()


# --- Rule-based parsing -----------------------------------------------------


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("Give me an overview of Fenton Village", Intent.COMMUNITY_OVERVIEW),
        ("Tell me about this area", Intent.COMMUNITY_OVERVIEW),
        ("What is the population?", Intent.POPULATION),
        ("How many people live here?", Intent.POPULATION),
        ("What is the median household income?", Intent.INCOME),
        ("Do people here earn a lot?", Intent.INCOME),
        ("What is the age profile?", Intent.AGE),
        ("Are residents young?", Intent.AGE),
        ("How many people rent?", Intent.HOUSING),
        ("What is the housing tenure?", Intent.HOUSING),
        ("How do people commute to work?", Intent.COMMUTE),
        ("Do people use public transport?", Intent.COMMUTE),
        ("What kinds of businesses are here?", Intent.BUSINESS_CATEGORIES),
        ("Show me the business mix", Intent.BUSINESS_CATEGORIES),
        ("How many restaurants are nearby?", Intent.NEARBY_BUSINESSES),
        ("Where are the cafes?", Intent.NEARBY_BUSINESSES),
    ],
)
def test_rule_based_intents(question: str, expected: Intent) -> None:
    parsed = rule_based_parse(question)

    assert parsed is not None, question
    assert parsed.intent is expected


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("How many cafes are nearby?", "Cafe"),
        ("Where can I get coffee?", "Cafe"),
        ("Are there any bakeries?", "Bakery"),
        ("Show me pharmacies", "Health Services"),
        ("Find a bike shop", "Bike Shop"),
        ("How many restaurants?", "Restaurant"),
    ],
)
def test_category_detection(question: str, expected: str) -> None:
    parsed = rule_based_parse(question)

    assert parsed is not None
    assert parsed.business_category == expected


def test_category_question_beats_generic_category_intent() -> None:
    """"What kinds of restaurants" is about restaurants, not the category mix."""
    parsed = rule_based_parse("What kinds of businesses like restaurants are here?")

    assert parsed is not None
    assert parsed.intent is Intent.NEARBY_BUSINESSES
    assert parsed.business_category == "Restaurant"


@pytest.mark.parametrize(
    "question",
    [
        "What is the meaning of life?",
        "Write me a poem",
        "asdfghjkl",
        "   ",
        "Who won the World Cup?",
    ],
)
def test_unsupported_questions_do_not_parse(question: str) -> None:
    """No guessing: an unmatched question is refused, not approximated."""
    assert rule_based_parse(question) is None


# --- Classifier validation --------------------------------------------------


def test_valid_classifier_output_is_accepted() -> None:
    parsed = validate_classifier_output(
        {"intent": "income", "geography": "fenton-village", "business_category": None}
    )

    assert parsed is not None
    assert parsed.intent is Intent.INCOME


@pytest.mark.parametrize(
    "payload",
    [
        None,
        "not a dict",
        {},
        {"intent": "hack_the_database"},
        {"intent": "DROP TABLE businesses"},
        [1, 2, 3],
    ],
)
def test_malformed_classifier_output_is_rejected(payload: object) -> None:
    assert validate_classifier_output(payload) is None


def test_classifier_cannot_supply_statistics() -> None:
    """The central safety property.

    A model that tries to return a number alongside the intent is rejected
    entirely, because ParsedQuery forbids extra fields. There is no path by
    which a model-supplied figure reaches the response.
    """
    payload = {
        "intent": "population",
        "geography": "fenton-village",
        "business_category": None,
        "population": 99999,
        "answer": "The population is 99,999.",
    }

    assert validate_classifier_output(payload) is None


def test_invented_category_is_dropped_but_intent_kept() -> None:
    parsed = validate_classifier_output(
        {
            "intent": "nearby_businesses",
            "geography": "fenton-village",
            "business_category": "Artisanal Cheese Emporium",
        }
    )

    assert parsed is not None
    assert parsed.intent is Intent.NEARBY_BUSINESSES
    assert parsed.business_category is None


# --- Classifier fallback ----------------------------------------------------


def test_classifier_is_used_when_it_returns_valid_output() -> None:
    def classifier(question: str) -> dict:
        return {"intent": "housing", "geography": "fenton-village", "business_category": None}

    parsed = parse_question("something ambiguous", classifier=classifier)

    assert parsed is not None
    assert parsed.intent is Intent.HOUSING


def test_falls_back_to_keywords_when_classifier_raises() -> None:
    """An LLM outage must not take the demo down."""

    def broken(question: str) -> dict:
        raise RuntimeError("API unavailable")

    parsed = parse_question("What is the population?", classifier=broken)

    assert parsed is not None
    assert parsed.intent is Intent.POPULATION


def test_falls_back_when_classifier_returns_garbage() -> None:
    parsed = parse_question(
        "What is the median household income?",
        classifier=lambda q: {"intent": "nonsense"},
    )

    assert parsed is not None
    assert parsed.intent is Intent.INCOME


def test_no_classifier_configured_still_works() -> None:
    """The default path: no model involved at all."""
    parsed = parse_question("How do people commute?")

    assert parsed is not None
    assert parsed.intent is Intent.COMMUTE


# --- Endpoint: happy paths --------------------------------------------------


def test_population_question(client: TestClient, db_session: Session) -> None:
    _seed(db_session)

    payload = _ask(client, "What is the population?")

    assert payload["understood"] is True
    assert payload["parsed"]["intent"] == "population"
    assert "4,000" in payload["answer"]
    assert any(m["key"] == "total_population" for m in payload["metrics"])
    assert payload["evidence"]


def test_income_question_reports_a_range(
    client: TestClient, db_session: Session
) -> None:
    _seed(db_session)

    payload = _ask(client, "What is the median household income?")

    assert payload["parsed"]["intent"] == "income"
    income = payload["ranges"][0]
    assert income["minimum"] == 80000.0
    assert income["maximum"] == 140000.0
    assert any("median" in limitation.lower() for limitation in payload["limitations"])


def test_housing_question(client: TestClient, db_session: Session) -> None:
    _seed(db_session)

    payload = _ask(client, "How many people rent versus own?")

    assert payload["parsed"]["intent"] == "housing"
    keys = {m["key"] for m in payload["metrics"]}
    assert {"renter_occupied_households", "owner_occupied_households", "renter_share"} <= keys
    assert "35%" in payload["answer"]


def test_commute_question(client: TestClient, db_session: Session) -> None:
    _seed(db_session)

    payload = _ask(client, "How do people commute to work?")

    assert payload["parsed"]["intent"] == "commute"
    assert any(m["key"] == "commute_active_share" for m in payload["metrics"])


def test_business_categories_question(
    client: TestClient, db_session: Session
) -> None:
    _seed(db_session)

    payload = _ask(client, "What kinds of businesses are here?")

    assert payload["parsed"]["intent"] == "business_categories"
    assert payload["categories"][0]["category"] == "Restaurant"
    assert payload["categories"][0]["count"] == 5


def test_nearby_businesses_question(client: TestClient, db_session: Session) -> None:
    _seed(db_session)

    payload = _ask(client, "How many cafes are nearby?")

    assert payload["parsed"]["intent"] == "nearby_businesses"
    assert payload["parsed"]["business_category"] == "Cafe"
    assert len(payload["businesses"]) == 3
    assert payload["answer"] == (
        "3 of 10 mapped establishments in the study area are in the category 'Cafe'."
    )


def test_nearby_businesses_includes_map_points(
    client: TestClient, db_session: Session
) -> None:
    _seed(db_session)

    payload = _ask(client, "Where are the cafes?")

    features = payload["map"]["businesses"]["features"]
    assert len(features) == 3
    assert all(f["geometry"]["type"] == "Point" for f in features)


def test_zero_results_is_an_honest_answer(
    client: TestClient, db_session: Session
) -> None:
    """An empty category says so, rather than implying a market gap."""
    _seed(db_session)

    payload = _ask(client, "Are there any bakeries?")

    assert payload["businesses"] == []
    assert "No businesses in the category 'Bakery'" in payload["answer"]
    assert "does not exist" in " ".join(payload["limitations"])


def test_overview_question(client: TestClient, db_session: Session) -> None:
    _seed(db_session)

    payload = _ask(client, "Give me an overview of Fenton Village")

    assert payload["parsed"]["intent"] == "community_overview"
    assert payload["metrics"]
    assert payload["evidence"]


# --- Endpoint: rejection and safety ----------------------------------------


def test_unsupported_question_returns_suggestions(client: TestClient) -> None:
    payload = _ask(client, "What is the airspeed velocity of an unladen swallow?")

    assert payload["understood"] is False
    assert payload["parsed"] is None
    assert payload["metrics"] == []
    assert payload["suggestions"] == list(SUGGESTED_QUESTIONS)


def test_empty_question_is_rejected_by_validation(client: TestClient) -> None:
    assert client.post(ENDPOINT, json={"question": ""}).status_code == 422


def test_overlong_question_is_rejected(client: TestClient) -> None:
    assert client.post(ENDPOINT, json={"question": "a" * 501}).status_code == 422


def test_missing_question_field_is_rejected(client: TestClient) -> None:
    assert client.post(ENDPOINT, json={}).status_code == 422


@pytest.mark.parametrize(
    "question",
    [
        "'; DROP TABLE businesses; --",
        "SELECT * FROM data_sources",
        "{{ 7*7 }}",
        "../../etc/passwd",
    ],
)
def test_injection_attempts_are_treated_as_ordinary_text(
    client: TestClient, db_session: Session, question: str
) -> None:
    """Nothing in a question reaches a query builder.

    The intent enum is closed, so an unparseable question can only ever
    produce the unsupported response.
    """
    _seed(db_session)

    payload = _ask(client, question)

    assert payload["understood"] is False
    assert payload["metrics"] == []


def test_answers_contain_no_model_generated_numbers(
    client: TestClient, db_session: Session
) -> None:
    """Every figure in the answer traces to a stored value."""
    _seed(db_session)

    payload = _ask(client, "What is the population?")

    # 4000 = 1000 + 3000 from the seeded tracts.
    assert "4,000" in payload["answer"]
    stored = {m["key"]: m["value"] for m in payload["metrics"]}
    assert stored["total_population"] == 4000.0


def test_every_reported_metric_carries_evidence(
    client: TestClient, db_session: Session
) -> None:
    _seed(db_session)

    for question in (
        "What is the population?",
        "How many people rent?",
        "How do people commute?",
    ):
        payload = _ask(client, question)
        for metric in payload["metrics"]:
            if metric["available"]:
                assert metric["evidence"], f"{metric['key']} lacks evidence"
        assert payload["evidence"]


def test_limitations_always_state_the_study_area_caveat(
    client: TestClient, db_session: Session
) -> None:
    _seed(db_session)

    payload = _ask(client, "What is the population?")

    assert any("not a Census geography" in item for item in payload["limitations"])


def test_empty_database_does_not_error(client: TestClient) -> None:
    """A question against no data answers honestly rather than failing."""
    payload = _ask(client, "What is the population?")

    assert payload["understood"] is True
    assert "No data has been ingested" in payload["answer"]


def test_response_contract_fields_present(
    client: TestClient, db_session: Session
) -> None:
    _seed(db_session)

    payload = _ask(client, "How many cafes are nearby?")

    for field in (
        "question", "answer", "metrics", "businesses", "map", "evidence", "limitations"
    ):
        assert field in payload
    assert payload["question"] == "How many cafes are nearby?"
