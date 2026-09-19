"""Deterministic insight assembly.

Everything here is arithmetic over stored values. No model, no heuristic, no
recommendation. Given the same database, this module always produces the same
output.

Three rules it enforces:

1. **Counts are summed across tracts; medians are not.** The mean of fourteen
   tract medians is not the district median - a median is not additive, and
   computing one would be inventing a statistic. Medians are reported as a
   range across tracts, and the district-level median is explicitly marked
   unavailable.
2. **Shares are recomputed from summed components**, never averaged from
   per-tract shares, which would weight a 300-person tract equally with a
   6,000-person one.
3. **Missing stays missing.** A metric absent from a tract is never treated
   as zero; coverage is reported instead.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import CommunityMetric, Geography
from app.repositories import (
    BusinessRepository,
    CommunityMetricRepository,
    GeographyRepository,
)
from app.schemas.evidence import Evidence
from app.schemas.insights import (
    BusinessLandscape,
    CategoryBreakdown,
    Coverage,
    Derivation,
    InsightsResponse,
    Observation,
    SnapshotValue,
    StudyArea,
    UnavailableItem,
    ValueRange,
)

FENTON_VILLAGE_NAME = "Fenton Village, Silver Spring, Maryland"

STUDY_AREA_METHOD = (
    "Fenton Village is a commercial district and is not a Census geography: it "
    "has no GEOID and no published estimates. Figures here are aggregated from "
    "the Census tracts intersecting a project-defined bounding box over "
    "downtown Silver Spring. They are approximations of the district, not "
    "published estimates for it, and tracts extend beyond the commercial "
    "district itself."
)

MEDIAN_NOT_AGGREGATABLE = (
    "A district-level median cannot be derived from tract-level medians: "
    "medians are not additive, and averaging them would produce a number the "
    "source data does not support. The range across tracts is reported instead."
)


@dataclass(frozen=True)
class Aggregate:
    """A summed metric plus how much of the area it covers."""

    total: float | None
    tracts_with_data: int
    tracts_total: int
    evidence: list[Evidence]

    @property
    def coverage(self) -> Coverage:
        return Coverage(
            tracts_with_data=self.tracts_with_data,
            tracts_total=self.tracts_total,
            complete=self.tracts_with_data == self.tracts_total,
        )


def _evidence(metric: CommunityMetric) -> Evidence:
    return Evidence(
        dataset=metric.dataset,
        dataset_year=metric.dataset_year,
        source_variable=metric.source_variable,
        source_url=metric.source_url,
        organization=metric.data_source.organization,
    )


def _metrics_by_key(
    session: Session, geographies: list[Geography]
) -> dict[str, list[CommunityMetric]]:
    """Index every metric across the study area by metric key."""
    repository = CommunityMetricRepository(session)
    indexed: dict[str, list[CommunityMetric]] = {}
    for geography in geographies:
        for metric in repository.list_for_geography(geography.id):
            indexed.setdefault(metric.metric_key, []).append(metric)
    return indexed


def sum_metric(
    indexed: dict[str, list[CommunityMetric]], key: str, tracts_total: int
) -> Aggregate:
    """Sum one metric across tracts, ignoring tracts where it is null.

    A null is skipped rather than counted as zero, and the number of tracts
    that contributed is reported so a partial total is visible as partial.
    """
    metrics = indexed.get(key, [])
    values = [m.value for m in metrics if m.value is not None]
    evidence = [_evidence(metrics[0])] if metrics else []
    return Aggregate(
        total=sum(values) if values else None,
        tracts_with_data=len(values),
        tracts_total=tracts_total,
        evidence=evidence,
    )


def range_metric(
    indexed: dict[str, list[CommunityMetric]],
    key: str,
    label: str,
    unit: str,
    tracts_total: int,
) -> ValueRange:
    """Report a non-additive metric as its range across tracts."""
    metrics = indexed.get(key, [])
    values = [m.value for m in metrics if m.value is not None]
    if not values:
        return ValueRange(
            key=key,
            label=label,
            unit=unit,
            available=False,
            unavailable_reason=f"No tract in the study area reports {key}.",
            coverage=Coverage(
                tracts_with_data=0, tracts_total=tracts_total, complete=False
            ),
        )
    return ValueRange(
        key=key,
        label=label,
        minimum=min(values),
        maximum=max(values),
        unit=unit,
        available=True,
        coverage=Coverage(
            tracts_with_data=len(values),
            tracts_total=tracts_total,
            complete=len(values) == tracts_total,
        ),
        evidence=[_evidence(metrics[0])],
    )


def _count_value(aggregate: Aggregate, key: str, label: str, unit: str) -> SnapshotValue:
    """Wrap a summed count as a snapshot entry."""
    if aggregate.total is None:
        return SnapshotValue(
            key=key,
            label=label,
            unit=unit,
            available=False,
            unavailable_reason=f"No tract in the study area reports {key}.",
            coverage=aggregate.coverage,
        )
    return SnapshotValue(
        key=key,
        label=label,
        value=aggregate.total,
        unit=unit,
        available=True,
        derivation=Derivation(
            method="sum",
            formula=f"sum({key}) across {aggregate.tracts_with_data} tracts",
            numerator_metrics=[key],
            numerator_value=aggregate.total,
        ),
        coverage=aggregate.coverage,
        evidence=aggregate.evidence,
    )


def ratio_value(
    *,
    key: str,
    label: str,
    numerator: Aggregate,
    denominator: Aggregate,
    numerator_key: str,
    denominator_key: str,
) -> SnapshotValue:
    """Compute a percentage from two summed components.

    Recomputed from the totals rather than averaged from per-tract shares, so
    each tract contributes in proportion to its size.
    """
    if numerator.total is None or denominator.total is None:
        missing = numerator_key if numerator.total is None else denominator_key
        return SnapshotValue(
            key=key,
            label=label,
            unit="percent",
            available=False,
            unavailable_reason=f"Required metric {missing} is not available.",
            coverage=denominator.coverage,
        )
    if denominator.total == 0:
        return SnapshotValue(
            key=key,
            label=label,
            unit="percent",
            available=False,
            unavailable_reason=(
                f"{denominator_key} is zero across the study area, so the share "
                "is undefined rather than zero."
            ),
            coverage=denominator.coverage,
        )

    return SnapshotValue(
        key=key,
        label=label,
        value=round(numerator.total / denominator.total * 100, 2),
        unit="percent",
        available=True,
        derivation=Derivation(
            method="ratio",
            formula=f"sum({numerator_key}) / sum({denominator_key}) * 100",
            numerator_metrics=[numerator_key],
            denominator_metric=denominator_key,
            numerator_value=numerator.total,
            denominator_value=denominator.total,
        ),
        coverage=denominator.coverage,
        evidence=numerator.evidence + denominator.evidence,
    )


def build_business_landscape(session: Session) -> BusinessLandscape:
    """Category counts and shares over the mapped businesses."""
    repository = BusinessRepository(session)
    counts = repository.category_counts()
    total = sum(count for _, count in counts)

    businesses = repository.search(limit=1)
    evidence = (
        [
            Evidence(
                dataset=businesses[0].data_source.dataset,
                dataset_year=businesses[0].data_source.dataset_year,
                source_variable=None,
                source_url=businesses[0].source_url,
                organization=businesses[0].data_source.organization,
            )
        ]
        if businesses
        else []
    )

    return BusinessLandscape(
        total_businesses=total,
        category_count=len(counts),
        categories=[
            CategoryBreakdown(
                category=category,
                count=count,
                share_of_total=round(count / total * 100, 2) if total else 0.0,
            )
            for category, count in counts
        ],
        evidence=evidence,
    )


def _share_observation(
    value: SnapshotValue, observation_id: str, topic: str, template: str
) -> Observation | None:
    """Build an observation from an available share, or nothing."""
    if not value.available or value.value is None or value.derivation is None:
        return None
    return Observation(
        id=observation_id,
        statement=template.format(
            percent=f"{value.value:g}",
            numerator=f"{value.derivation.numerator_value:,.0f}",
            denominator=f"{value.derivation.denominator_value:,.0f}",
        ),
        topic=topic,
        basis_metrics=[
            *value.derivation.numerator_metrics,
            *( [value.derivation.denominator_metric]
               if value.derivation.denominator_metric else [] ),
        ],
        derivation=value.derivation,
        evidence=value.evidence,
    )


def build_observations(
    snapshot: dict[str, SnapshotValue],
    ranges: dict[str, ValueRange],
    landscape: BusinessLandscape,
    tract_count: int,
) -> list[Observation]:
    """Factual statements about the stored data.

    Every statement reports what the dataset contains. None recommends an
    action, and none asserts that one measured thing causes another.
    """
    observations: list[Observation] = []

    # --- Business landscape -------------------------------------------------
    if landscape.categories and landscape.total_businesses:
        top = landscape.categories[0]
        observations.append(
            Observation(
                id="largest_business_category",
                statement=(
                    f"{top.category} is the largest business category in the "
                    f"current dataset, with {top.count} of "
                    f"{landscape.total_businesses} mapped establishments "
                    f"({top.share_of_total:g}%)."
                ),
                topic="business_landscape",
                basis_metrics=["business_category_counts"],
                derivation=Derivation(
                    method="ratio",
                    formula=(
                        f"count(category = '{top.category}') / "
                        "count(all mapped businesses) * 100"
                    ),
                    numerator_value=float(top.count),
                    denominator_value=float(landscape.total_businesses),
                ),
                evidence=landscape.evidence,
            )
        )
        observations.append(
            Observation(
                id="business_category_spread",
                statement=(
                    f"{landscape.total_businesses} businesses are mapped across "
                    f"{landscape.category_count} categories in the current dataset."
                ),
                topic="business_landscape",
                basis_metrics=["business_category_counts"],
                evidence=landscape.evidence,
            )
        )

    # --- Community ----------------------------------------------------------
    population = snapshot.get("total_population")
    if population and population.available and population.value is not None:
        observations.append(
            Observation(
                id="resident_population",
                statement=(
                    f"The {tract_count} Census tracts covering the study area "
                    f"report a combined population of {population.value:,.0f}."
                ),
                topic="community_snapshot",
                basis_metrics=["total_population"],
                derivation=population.derivation,
                evidence=population.evidence,
            )
        )

    templates = [
        (
            "renter_share",
            "housing",
            "Renter-occupied households are {percent}% of occupied housing "
            "units in the study area ({numerator} of {denominator}).",
        ),
        (
            "young_adult_share",
            "age_composition",
            "Residents aged 18 to 34 are {percent}% of the population in the "
            "study area ({numerator} of {denominator}).",
        ),
        (
            "commute_active_share",
            "commuting",
            "{percent}% of workers in the study area commute by public "
            "transport, walking or cycling ({numerator} of {denominator}).",
        ),
        (
            "worked_from_home_share",
            "commuting",
            "{percent}% of workers in the study area worked from home "
            "({numerator} of {denominator}).",
        ),
        (
            "multilingual_household_share",
            "community_snapshot",
            "{percent}% of households in the study area speak a language other "
            "than English at home ({numerator} of {denominator}).",
        ),
        (
            "bachelors_or_higher_share",
            "community_snapshot",
            "{percent}% of residents aged 25 and over hold a bachelor's degree "
            "or higher ({numerator} of {denominator}).",
        ),
    ]
    for key, topic, template in templates:
        value = snapshot.get(key)
        if value is not None:
            observation = _share_observation(value, key, topic, template)
            if observation is not None:
                observations.append(observation)

    # --- Ranges -------------------------------------------------------------
    income = ranges.get("median_household_income")
    if income and income.available:
        observations.append(
            Observation(
                id="median_income_range",
                statement=(
                    "Median household income varies across the "
                    f"{income.coverage.tracts_with_data if income.coverage else 0} "
                    f"tracts reporting it, from ${income.minimum:,.0f} to "
                    f"${income.maximum:,.0f}."
                ),
                topic="income",
                basis_metrics=["median_household_income"],
                derivation=Derivation(
                    method="range",
                    formula="min and max of median_household_income across tracts",
                    numerator_metrics=["median_household_income"],
                ),
                evidence=income.evidence,
            )
        )

    age = ranges.get("median_age")
    if age and age.available:
        observations.append(
            Observation(
                id="median_age_range",
                statement=(
                    f"Median age ranges from {age.minimum:g} to {age.maximum:g} "
                    "years across the tracts in the study area."
                ),
                topic="age_composition",
                basis_metrics=["median_age"],
                derivation=Derivation(
                    method="range",
                    formula="min and max of median_age across tracts",
                    numerator_metrics=["median_age"],
                ),
                evidence=age.evidence,
            )
        )

    return observations


def build_insights(session: Session) -> InsightsResponse:
    """Assemble the deterministic summary for the Fenton Village study area."""
    geographies = GeographyRepository(session).list_with_geometry()
    tract_count = len(geographies)
    indexed = _metrics_by_key(session, geographies)

    def total(key: str) -> Aggregate:
        return sum_metric(indexed, key, tract_count)

    population = total("total_population")
    young_adults = total("young_adults_18_34")
    households = total("occupied_housing_units")
    renters = total("renter_occupied_households")
    owners = total("owner_occupied_households")
    workers = total("commuters_total")
    transit = total("commute_public_transport")
    walked = total("commute_walked")
    cycled = total("commute_bicycle")
    from_home = total("worked_from_home")
    language_total = total("multilingual_households")
    # C16002's household universe, not B25003's occupied housing units.
    language_base = total("language_households_total")
    graduates = total("bachelors_or_higher")
    # B15003 counts only adults 25+, so total population is not a valid base.
    education_base = total("adults_25_plus")

    # Active commuting sums three modes, so it gets its own aggregate rather
    # than reusing ratio_value's single-numerator path.
    active_values = [a.total for a in (transit, walked, cycled)]
    active_total = (
        sum(v for v in active_values if v is not None)
        if all(v is not None for v in active_values)
        else None
    )
    active = Aggregate(
        total=active_total,
        tracts_with_data=min(
            a.tracts_with_data for a in (transit, walked, cycled)
        ),
        tracts_total=tract_count,
        evidence=transit.evidence,
    )

    snapshot_values = [
        _count_value(population, "total_population", "Population", "people"),
        _count_value(households, "occupied_housing_units", "Occupied housing units", "households"),
        _count_value(young_adults, "young_adults_18_34", "Residents aged 18-34", "people"),
        _count_value(transit, "commute_public_transport", "Public transport commuters", "people"),
        _count_value(renters, "renter_occupied_households", "Renter-occupied households", "households"),
        _count_value(owners, "owner_occupied_households", "Owner-occupied households", "households"),
        _count_value(workers, "commuters_total", "Workers aged 16+", "people"),
        _count_value(education_base, "adults_25_plus", "Residents aged 25+", "people"),
        ratio_value(
            key="renter_share", label="Renter-occupied share",
            numerator=renters, denominator=households,
            numerator_key="renter_occupied_households",
            denominator_key="occupied_housing_units",
        ),
        ratio_value(
            key="young_adult_share", label="Share aged 18-34",
            numerator=young_adults, denominator=population,
            numerator_key="young_adults_18_34", denominator_key="total_population",
        ),
        ratio_value(
            key="commute_active_share", label="Transit, walking or cycling share",
            numerator=active, denominator=workers,
            numerator_key="commute_public_transport + commute_walked + commute_bicycle",
            denominator_key="commuters_total",
        ),
        ratio_value(
            key="commute_transit_share", label="Public transport share",
            numerator=transit, denominator=workers,
            numerator_key="commute_public_transport",
            denominator_key="commuters_total",
        ),
        ratio_value(
            key="worked_from_home_share", label="Worked-from-home share",
            numerator=from_home, denominator=workers,
            numerator_key="worked_from_home", denominator_key="commuters_total",
        ),
        ratio_value(
            key="multilingual_household_share", label="Multilingual household share",
            numerator=language_total, denominator=language_base,
            numerator_key="multilingual_households",
            denominator_key="language_households_total",
        ),
        ratio_value(
            key="bachelors_or_higher_share", label="Bachelor's degree or higher share",
            numerator=graduates, denominator=education_base,
            numerator_key="bachelors_or_higher", denominator_key="adults_25_plus",
        ),
    ]

    value_ranges = [
        range_metric(indexed, "median_household_income", "Median household income", "usd", tract_count),
        range_metric(indexed, "median_age", "Median age", "years", tract_count),
    ]

    landscape = build_business_landscape(session)
    snapshot_by_key = {value.key: value for value in snapshot_values}
    ranges_by_key = {value.key: value for value in value_ranges}

    unavailable = [
        UnavailableItem(key="median_household_income_district", reason=MEDIAN_NOT_AGGREGATABLE),
        UnavailableItem(key="median_age_district", reason=MEDIAN_NOT_AGGREGATABLE),
    ]
    unavailable.extend(
        UnavailableItem(
            key=value.key, reason=value.unavailable_reason or "Not available."
        )
        for value in snapshot_values
        if not value.available
    )

    return InsightsResponse(
        study_area=StudyArea(
            name=FENTON_VILLAGE_NAME,
            tract_count=tract_count,
            tract_geoids=[g.geoid for g in geographies],
            method=STUDY_AREA_METHOD,
        ),
        community_snapshot=snapshot_values,
        ranges=value_ranges,
        business_landscape=landscape,
        observations=build_observations(
            snapshot_by_key, ranges_by_key, landscape, tract_count
        ),
        unavailable=unavailable,
    )
