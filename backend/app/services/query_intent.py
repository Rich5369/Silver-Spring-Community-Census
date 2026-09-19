"""Intent parsing.

Two parsers, in order:

1. An optional classifier (a language model, if one is configured). Its
   output is validated against :class:`~app.schemas.query.ParsedQuery` and
   discarded entirely if it does not fit.
2. A deterministic keyword parser, always available.

The rule-based parser is not merely a fallback for outages - it is what runs
by default. No language model is configured in this project, so the demo
works offline and the test suite needs no API key.
"""

from __future__ import annotations

import re
from typing import Protocol

from pydantic import ValidationError

from app.integrations.osm_categories import BUSINESS_CATEGORIES
from app.schemas.query import FENTON_VILLAGE, Intent, ParsedQuery


class IntentClassifier(Protocol):
    """Anything that can propose a structured query from a question.

    Deliberately narrow: an implementation returns a mapping that must
    validate as a ParsedQuery. It is given no way to return facts.
    """

    def __call__(self, question: str) -> dict | None: ...


# --- Category synonyms ------------------------------------------------------
# Maps everyday words onto the fixed taxonomy. Longer phrases first so
# "coffee shop" is not shadowed by "shop".
_CATEGORY_SYNONYMS: tuple[tuple[str, str], ...] = (
    ("coffee shop", "Cafe"),
    ("coffee", "Cafe"),
    ("cafes", "Cafe"),
    ("cafe", "Cafe"),
    ("café", "Cafe"),
    ("restaurants", "Restaurant"),
    ("restaurant", "Restaurant"),
    ("food", "Restaurant"),
    ("dining", "Restaurant"),
    ("bakeries", "Bakery"),
    ("bakery", "Bakery"),
    ("groceries", "Grocery"),
    ("grocery", "Grocery"),
    ("supermarket", "Grocery"),
    ("pharmacies", "Health Services"),
    ("pharmacy", "Health Services"),
    ("doctor", "Health Services"),
    ("dentist", "Health Services"),
    ("health", "Health Services"),
    ("salon", "Personal Care"),
    ("hairdresser", "Personal Care"),
    ("barber", "Personal Care"),
    ("beauty", "Personal Care"),
    ("pet", "Pet Services"),
    ("vet", "Pet Services"),
    ("florist", "Florist"),
    ("flowers", "Florist"),
    ("bike", "Bike Shop"),
    ("bicycle", "Bike Shop"),
    ("computer", "Technology Services"),
    ("phone", "Technology Services"),
    ("electronics", "Technology Services"),
    ("bank", "Professional Services"),
    ("laundry", "Professional Services"),
    ("retail", "Retail"),
    ("shops", "Retail"),
    ("stores", "Retail"),
    ("store", "Retail"),
)

# --- Intent keywords --------------------------------------------------------
# Ordered most specific to most general; the first intent with a match wins.
_INTENT_KEYWORDS: tuple[tuple[Intent, tuple[str, ...]], ...] = (
    (
        Intent.BUSINESS_CATEGORIES,
        (
            "what kind of business", "what kinds of business", "what types of business",
            "business categories", "categories of business", "types of business",
            "kinds of business", "business mix", "what businesses are",
            "breakdown of business", "business landscape",
        ),
    ),
    (
        Intent.COMMUTE,
        (
            "commute", "commuting", "transit", "public transport", "drive to work",
            "get to work", "walk to work", "travel to work", "work from home",
            "remote work", "transportation",
        ),
    ),
    (
        Intent.HOUSING,
        (
            "rent", "renter", "renters", "own", "owner", "homeowner", "housing",
            "tenure", "households", "apartment",
        ),
    ),
    (
        Intent.INCOME,
        ("income", "earn", "earnings", "salary", "wealth", "affluent", "wages"),
    ),
    (
        Intent.AGE,
        ("age", "ages", "old", "young", "younger", "millennial", "demographic profile"),
    ),
    (
        Intent.POPULATION,
        ("population", "how many people", "how many residents", "residents", "people live"),
    ),
    (
        Intent.NEARBY_BUSINESSES,
        (
            "nearby", "near me", "how many", "list", "show me", "where are",
            "are there any", "find",
        ),
    ),
    (
        Intent.COMMUNITY_OVERVIEW,
        ("overview", "summary", "summarise", "summarize", "tell me about", "describe", "profile"),
    ),
)


def _normalise(question: str) -> str:
    return re.sub(r"\s+", " ", question.strip().lower())


def _mentions(text: str, term: str) -> bool:
    """Whether ``term`` appears in ``text`` as a whole word or phrase.

    Word boundaries are essential rather than cosmetic here: plain substring
    matching makes "age" match "Village", "own" match "downtown", "rent"
    match "different" and "old" match "household" - each of which routes a
    question to the wrong intent with no visible error.
    """
    # A trailing plural is tolerated so "kinds of business" matches "kinds of
    # businesses" and "cafe" matches "cafes", without a plural entry for
    # every term.
    return re.search(rf"\b{re.escape(term)}(?:e?s)?\b", text) is not None


def detect_category(question: str) -> str | None:
    """Find a taxonomy category mentioned in the question, if any."""
    text = _normalise(question)
    for term, category in _CATEGORY_SYNONYMS:
        if _mentions(text, term):
            return category
    # Allow an exact taxonomy name, e.g. "Health Services".
    for category in BUSINESS_CATEGORIES:
        if _mentions(text, category.lower()):
            return category
    return None


def rule_based_parse(question: str) -> ParsedQuery | None:
    """Classify a question using keywords alone.

    Returns ``None`` when nothing matches, which the caller turns into an
    explicit "not supported" answer rather than a guess.
    """
    text = _normalise(question)
    if not text:
        return None

    category = detect_category(question)

    for intent, keywords in _INTENT_KEYWORDS:
        if any(_mentions(text, keyword) for keyword in keywords):
            # A question naming a business type is about those businesses,
            # even when phrased with a generic verb such as "how many".
            if intent is Intent.BUSINESS_CATEGORIES and category:
                intent = Intent.NEARBY_BUSINESSES
            return ParsedQuery(
                intent=intent,
                geography=FENTON_VILLAGE,
                business_category=(
                    category if intent is Intent.NEARBY_BUSINESSES else None
                ),
            )

    # A bare category name ("cafes?") is a business question.
    if category:
        return ParsedQuery(
            intent=Intent.NEARBY_BUSINESSES,
            geography=FENTON_VILLAGE,
            business_category=category,
        )

    return None


def validate_classifier_output(payload: object) -> ParsedQuery | None:
    """Validate a classifier's proposal, or reject it.

    Anything that is not exactly a ParsedQuery - a bad intent, an extra
    field, an invented category - is discarded. Nothing partially valid is
    salvaged, because a half-trusted parse is worse than a keyword match.
    """
    if not isinstance(payload, dict):
        return None
    try:
        parsed = ParsedQuery.model_validate(payload)
    except ValidationError:
        return None

    if parsed.business_category is not None and (
        parsed.business_category not in BUSINESS_CATEGORIES
    ):
        # The model invented a category. Keep the intent, drop the category.
        parsed = parsed.model_copy(update={"business_category": None})
    return parsed


def parse_question(
    question: str, classifier: IntentClassifier | None = None
) -> ParsedQuery | None:
    """Parse a question into a structured query.

    Tries the configured classifier first, then the keyword parser. Any
    failure in the classifier - exception, timeout, malformed output - falls
    through silently to the deterministic path, so the demo never depends on
    an external service being up.
    """
    if classifier is not None:
        try:
            proposal = classifier(question)
        except Exception:  # noqa: BLE001 - any classifier failure is non-fatal
            proposal = None
        parsed = validate_classifier_output(proposal)
        if parsed is not None:
            return parsed

    return rule_based_parse(question)
