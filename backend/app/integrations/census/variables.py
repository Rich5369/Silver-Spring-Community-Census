"""Centralised ACS variable catalogue and derived-metric definitions.

Every variable ID and label in this module was read from the live Census
metadata API for the 2024 ACS 5-Year release
(``https://api.census.gov/data/2024/acs/acs5/groups/<GROUP>.json``) rather
than recalled or inferred. Labels are reproduced verbatim, including the
``!!`` nesting separators the Census uses, so a reviewer can diff them
against the published metadata.

If a future release renames or retires a variable, this is the only module
that changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

# The ACS release these definitions were verified against. Changing this
# requires re-verifying every label below, because variable IDs are not
# guaranteed stable across releases.
ACS_YEAR: int = 2024
ACS_DATASET: str = "acs/acs5"
ACS_DATASET_TITLE: str = "American Community Survey 5-Year Estimates"


@dataclass(frozen=True)
class AcsVariable:
    """One ACS variable, with the Census's own description of it."""

    variable_id: str
    #: Verbatim ``label`` from the Census metadata API.
    label: str
    #: The table (group) the variable belongs to, e.g. "B19013".
    group: str
    #: Plain-language gloss for display to a non-specialist.
    description: str


def _v(variable_id: str, label: str, description: str) -> AcsVariable:
    return AcsVariable(
        variable_id=variable_id,
        label=label,
        group=variable_id.split("_", 1)[0],
        description=description,
    )


# --- Variable catalogue -----------------------------------------------------
# Verified against the 2024 ACS 5-Year metadata API on ingestion-layer build.

ACS_VARIABLES: dict[str, AcsVariable] = {
    v.variable_id: v
    for v in (
        # B01003 - Total Population
        _v("B01003_001E", "Estimate!!Total", "Total population"),
        # B01002 - Median Age by Sex
        _v("B01002_001E", "Estimate!!Median age --!!Total:", "Median age"),
        # B19013 - Median Household Income
        _v(
            "B19013_001E",
            "Estimate!!Median household income in the past 12 months "
            "(in 2024 inflation-adjusted dollars)",
            "Median household income, inflation-adjusted to 2024 dollars",
        ),
        # B01001 - Sex by Age. Young-adult cells, male then female.
        _v("B01001_001E", "Estimate!!Total:", "Total population (age table base)"),
        _v("B01001_008E", "Estimate!!Total:!!Male:!!20 years", "Men aged 20"),
        _v("B01001_009E", "Estimate!!Total:!!Male:!!21 years", "Men aged 21"),
        _v("B01001_010E", "Estimate!!Total:!!Male:!!22 to 24 years", "Men aged 22-24"),
        _v("B01001_011E", "Estimate!!Total:!!Male:!!25 to 29 years", "Men aged 25-29"),
        _v("B01001_012E", "Estimate!!Total:!!Male:!!30 to 34 years", "Men aged 30-34"),
        _v("B01001_032E", "Estimate!!Total:!!Female:!!20 years", "Women aged 20"),
        _v("B01001_033E", "Estimate!!Total:!!Female:!!21 years", "Women aged 21"),
        _v(
            "B01001_034E", "Estimate!!Total:!!Female:!!22 to 24 years", "Women aged 22-24"
        ),
        _v(
            "B01001_035E", "Estimate!!Total:!!Female:!!25 to 29 years", "Women aged 25-29"
        ),
        _v(
            "B01001_036E", "Estimate!!Total:!!Female:!!30 to 34 years", "Women aged 30-34"
        ),
        # B25003 - Tenure
        _v("B25003_001E", "Estimate!!Total:", "Occupied housing units"),
        _v("B25003_002E", "Estimate!!Total:!!Owner occupied", "Owner-occupied households"),
        _v(
            "B25003_003E",
            "Estimate!!Total:!!Renter occupied",
            "Renter-occupied households",
        ),
        # B08301 - Means of Transportation to Work
        _v("B08301_001E", "Estimate!!Total:", "Workers aged 16+ (commute table base)"),
        _v(
            "B08301_003E",
            "Estimate!!Total:!!Car, truck, or van:!!Drove alone",
            "Commuters who drove alone",
        ),
        _v(
            "B08301_004E",
            "Estimate!!Total:!!Car, truck, or van:!!Carpooled:",
            "Commuters who carpooled",
        ),
        _v(
            "B08301_010E",
            "Estimate!!Total:!!Public transportation:",
            "Commuters using public transportation",
        ),
        _v("B08301_018E", "Estimate!!Total:!!Bicycle", "Commuters who bicycled"),
        _v("B08301_019E", "Estimate!!Total:!!Walked", "Commuters who walked"),
        _v(
            "B08301_021E",
            "Estimate!!Total:!!Worked from home",
            "Workers who worked from home",
        ),
        # B15003 - Educational Attainment, population 25 years and over
        _v("B15003_001E", "Estimate!!Total:", "Population aged 25+ (education base)"),
        _v(
            "B15003_022E",
            "Estimate!!Total:!!Bachelor's degree",
            "Adults 25+ with a bachelor's degree",
        ),
        _v(
            "B15003_023E",
            "Estimate!!Total:!!Master's degree",
            "Adults 25+ with a master's degree",
        ),
        _v(
            "B15003_024E",
            "Estimate!!Total:!!Professional school degree",
            "Adults 25+ with a professional degree",
        ),
        _v(
            "B15003_025E",
            "Estimate!!Total:!!Doctorate degree",
            "Adults 25+ with a doctorate",
        ),
        # C16002 - Household Language by Limited English Speaking Status
        _v("C16002_001E", "Estimate!!Total:", "Total households (language table base)"),
        _v(
            "C16002_002E",
            "Estimate!!Total:!!English only",
            "Households speaking only English",
        ),
    )
}


# --- Derived metrics --------------------------------------------------------

MetricKind = Literal["direct", "sum", "difference", "share"]


@dataclass(frozen=True)
class MetricSpec:
    """How one stored metric is computed from ACS variables.

    Declarative rather than a callable so the definition is inspectable: the
    provenance written alongside each value is generated from these fields,
    which keeps the citation and the arithmetic from drifting apart.
    """

    metric_key: str
    description: str
    unit: str
    kind: MetricKind
    #: Inputs. For "share" these form the numerator.
    variable_ids: tuple[str, ...]
    #: "share" only: the denominator variable.
    denominator_id: str | None = None
    #: "difference" only: subtracted from the sum of ``variable_ids``.
    subtract_ids: tuple[str, ...] = field(default_factory=tuple)

    @property
    def all_variable_ids(self) -> tuple[str, ...]:
        """Every ACS variable this metric reads."""
        ids = list(self.variable_ids) + list(self.subtract_ids)
        if self.denominator_id:
            ids.append(self.denominator_id)
        return tuple(dict.fromkeys(ids))

    @property
    def source_variable(self) -> str:
        """Compact formula recorded as this metric's provenance.

        A single ID for a direct metric, otherwise the arithmetic, so a
        reader can reproduce the number from the published tables.
        """
        if self.kind == "direct":
            return self.variable_ids[0]
        if self.kind == "sum":
            return " + ".join(self.variable_ids)
        numerator = " + ".join(self.variable_ids)
        if self.subtract_ids:
            numerator = f"{numerator} - {' - '.join(self.subtract_ids)}"
        if self.kind == "difference":
            return numerator
        return f"({numerator}) / {self.denominator_id} * 100"


_YOUNG_ADULT_CELLS: tuple[str, ...] = (
    "B01001_008E",
    "B01001_009E",
    "B01001_010E",
    "B01001_011E",
    "B01001_012E",
    "B01001_032E",
    "B01001_033E",
    "B01001_034E",
    "B01001_035E",
    "B01001_036E",
)

_BACHELORS_PLUS_CELLS: tuple[str, ...] = (
    "B15003_022E",
    "B15003_023E",
    "B15003_024E",
    "B15003_025E",
)

METRIC_SPECS: tuple[MetricSpec, ...] = (
    # --- Market size --------------------------------------------------------
    MetricSpec(
        metric_key="total_population",
        description="Total population",
        unit="people",
        kind="direct",
        variable_ids=("B01003_001E",),
    ),
    MetricSpec(
        metric_key="median_household_income",
        description="Median household income (2024 inflation-adjusted dollars)",
        unit="usd",
        kind="direct",
        variable_ids=("B19013_001E",),
    ),
    # --- Age profile --------------------------------------------------------
    MetricSpec(
        metric_key="median_age",
        description="Median age",
        unit="years",
        kind="direct",
        variable_ids=("B01002_001E",),
    ),
    MetricSpec(
        metric_key="young_adults_20_34",
        description="Residents aged 20 to 34",
        unit="people",
        kind="sum",
        variable_ids=_YOUNG_ADULT_CELLS,
    ),
    MetricSpec(
        metric_key="young_adult_share",
        description="Share of residents aged 20 to 34",
        unit="percent",
        kind="share",
        variable_ids=_YOUNG_ADULT_CELLS,
        denominator_id="B01001_001E",
    ),
    # --- Housing tenure -----------------------------------------------------
    MetricSpec(
        metric_key="occupied_housing_units",
        description="Occupied housing units",
        unit="households",
        kind="direct",
        variable_ids=("B25003_001E",),
    ),
    MetricSpec(
        metric_key="owner_occupied_households",
        description="Owner-occupied households",
        unit="households",
        kind="direct",
        variable_ids=("B25003_002E",),
    ),
    MetricSpec(
        metric_key="renter_occupied_households",
        description="Renter-occupied households",
        unit="households",
        kind="direct",
        variable_ids=("B25003_003E",),
    ),
    MetricSpec(
        metric_key="renter_share",
        description="Share of occupied housing units that are renter-occupied",
        unit="percent",
        kind="share",
        variable_ids=("B25003_003E",),
        denominator_id="B25003_001E",
    ),
    # --- Commuting ----------------------------------------------------------
    MetricSpec(
        metric_key="commuters_total",
        description="Workers aged 16 and over",
        unit="people",
        kind="direct",
        variable_ids=("B08301_001E",),
    ),
    MetricSpec(
        metric_key="commute_drove_alone",
        description="Commuters who drove alone",
        unit="people",
        kind="direct",
        variable_ids=("B08301_003E",),
    ),
    MetricSpec(
        metric_key="commute_carpooled",
        description="Commuters who carpooled",
        unit="people",
        kind="direct",
        variable_ids=("B08301_004E",),
    ),
    MetricSpec(
        metric_key="commute_public_transport",
        description="Commuters using public transportation",
        unit="people",
        kind="direct",
        variable_ids=("B08301_010E",),
    ),
    MetricSpec(
        metric_key="commute_walked",
        description="Commuters who walked",
        unit="people",
        kind="direct",
        variable_ids=("B08301_019E",),
    ),
    MetricSpec(
        metric_key="commute_bicycle",
        description="Commuters who bicycled",
        unit="people",
        kind="direct",
        variable_ids=("B08301_018E",),
    ),
    MetricSpec(
        metric_key="worked_from_home",
        description="Workers who worked from home",
        unit="people",
        kind="direct",
        variable_ids=("B08301_021E",),
    ),
    MetricSpec(
        metric_key="commute_active_share",
        description="Share of workers who walked, cycled or used public transport",
        unit="percent",
        kind="share",
        variable_ids=("B08301_010E", "B08301_018E", "B08301_019E"),
        denominator_id="B08301_001E",
    ),
    MetricSpec(
        metric_key="worked_from_home_share",
        description="Share of workers who worked from home",
        unit="percent",
        kind="share",
        variable_ids=("B08301_021E",),
        denominator_id="B08301_001E",
    ),
    # --- Education ----------------------------------------------------------
    MetricSpec(
        metric_key="bachelors_or_higher",
        description="Adults aged 25 and over with a bachelor's degree or higher",
        unit="people",
        kind="sum",
        variable_ids=_BACHELORS_PLUS_CELLS,
    ),
    MetricSpec(
        metric_key="bachelors_or_higher_share",
        description="Share of adults aged 25+ with a bachelor's degree or higher",
        unit="percent",
        kind="share",
        variable_ids=_BACHELORS_PLUS_CELLS,
        denominator_id="B15003_001E",
    ),
    # --- Language -----------------------------------------------------------
    MetricSpec(
        metric_key="multilingual_households",
        description="Households speaking a language other than English at home",
        unit="households",
        kind="difference",
        variable_ids=("C16002_001E",),
        subtract_ids=("C16002_002E",),
    ),
    MetricSpec(
        metric_key="multilingual_household_share",
        description=(
            "Share of households speaking a language other than English at home"
        ),
        unit="percent",
        kind="share",
        variable_ids=("C16002_001E",),
        subtract_ids=("C16002_002E",),
        denominator_id="C16002_001E",
    ),
)

METRIC_SPECS_BY_KEY: dict[str, MetricSpec] = {s.metric_key: s for s in METRIC_SPECS}


def required_variable_ids() -> tuple[str, ...]:
    """Every ACS variable needed to compute the full metric set, deduplicated."""
    ids: list[str] = []
    for spec in METRIC_SPECS:
        ids.extend(spec.all_variable_ids)
    return tuple(dict.fromkeys(ids))
