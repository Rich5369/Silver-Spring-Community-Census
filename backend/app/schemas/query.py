"""Natural-language query schemas.

The boundary that makes this safe is :class:`ParsedQuery`. It is the *only*
thing a language model is ever allowed to produce: a closed set of intents, a
geography slug and an optional category. It carries no numbers, no prose and
no field a model could use to smuggle a statistic into the response. Every
factual value is read from the database afterwards.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.business import BusinessOut
from app.schemas.evidence import Evidence
from app.schemas.geojson import FeatureCollection
from app.schemas.insights import CategoryBreakdown, SnapshotValue, ValueRange
from app.schemas.trends import TrendSeries


class Intent(str, Enum):
    """The questions this endpoint can answer.

    A closed enum on purpose: an intent outside this set cannot be parsed,
    so it cannot reach retrieval. This is what stops the endpoint becoming a
    general-purpose chatbot.
    """

    COMMUNITY_OVERVIEW = "community_overview"
    POPULATION = "population"
    INCOME = "income"
    AGE = "age"
    HOUSING = "housing"
    COMMUTE = "commute"
    BUSINESS_CATEGORIES = "business_categories"
    NEARBY_BUSINESSES = "nearby_businesses"
    BUSINESS_OPPORTUNITY = "business_opportunity"
    GOVERNMENT_OVERVIEW = "government_overview"
    TRENDS = "trends"
    DIVERSITY = "diversity"
    DISPLACEMENT = "displacement"
    POLICY_SUPPORT = "policy_support"
    COMMUNITY_SUPPORT = "community_support"
    BUSINESS_HEALTH = "business_health"
    HEALTH_ACCESS = "health_access"


#: The only geography the MVP has data for.
FENTON_VILLAGE = "fenton-village"

SUPPORTED_GEOGRAPHIES: frozenset[str] = frozenset({FENTON_VILLAGE})

#: Shown to the user when a question cannot be answered.
SUGGESTED_QUESTIONS: tuple[str, ...] = (
    "Give me an overview of Fenton Village",
    "What is the population of Fenton Village?",
    "What is the median household income?",
    "What is the age profile of residents?",
    "How many people rent versus own their homes?",
    "How do people commute to work?",
    "What kinds of businesses are in the area?",
    "How many restaurants are nearby?",
    "Which business could be successful opening here?",
    "How has the community changed over time?",
    "What are the diversity indicators?",
    "Are there signs of housing displacement?",
    "What policy should the council prioritize?",
    "How can the city support this community?",
    "Are local businesses declining?",
    "Is access to health care declining?",
)


class ParsedQuery(BaseModel):
    """A validated structured query.

    This is the full extent of what intent parsing may produce. ``extra`` is
    forbidden so that a model returning additional keys - a "population"
    field, say - is rejected outright rather than partially trusted.
    """

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "intent": "nearby_businesses",
                "geography": "fenton-village",
                "business_category": "Cafe",
            }
        },
    )

    intent: Intent
    geography: str = Field(default=FENTON_VILLAGE)
    business_category: str | None = Field(
        default=None,
        description="A value from the fixed business taxonomy, or null.",
    )


class QueryRequest(BaseModel):
    """A question from the user."""

    model_config = ConfigDict(
        json_schema_extra={"example": {"question": "How many cafes are nearby?"}}
    )

    question: str = Field(
        min_length=1,
        max_length=500,
        description="A plain-language question about the Fenton Village data.",
    )


class QueryMap(BaseModel):
    """Map context for the answer.

    Business points are inlined because a category answer is small. Area
    boundaries are not: they are ~160 KB, so the endpoint that serves them is
    named instead of duplicating them in every response.
    """

    area_geoids: list[str] = Field(default_factory=list)
    businesses: FeatureCollection | None = None
    boundaries_endpoint: str = "/api/v1/map/community"


class QueryResponse(BaseModel):
    """An evidence-backed answer.

    ``answer`` is assembled from database values by fixed templates. It is
    never written by a language model, so it cannot contain a number the
    database does not hold.
    """

    question: str
    understood: bool = Field(
        description="False when the question did not match a supported intent."
    )
    parsed: ParsedQuery | None = Field(
        default=None, description="The validated structured query that was run."
    )
    answer: str
    metrics: list[SnapshotValue] = Field(default_factory=list)
    ranges: list[ValueRange] = Field(default_factory=list)
    categories: list[CategoryBreakdown] = Field(default_factory=list)
    businesses: list[BusinessOut] = Field(default_factory=list)
    map: QueryMap = Field(default_factory=QueryMap)
    evidence: list[Evidence] = Field(default_factory=list)
    trends: list[TrendSeries] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(
        default_factory=list,
        description="Supported questions, returned when one cannot be answered.",
    )
