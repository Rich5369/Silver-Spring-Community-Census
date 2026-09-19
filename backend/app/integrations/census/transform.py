"""Turn raw Census rows into metric records.

Pure functions: no HTTP, no database. That separation is what makes the
awkward parts - suppressed values, jurisdiction annotations, derived shares -
testable without touching either.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.integrations.census.variables import (
    METRIC_SPECS,
    MetricSpec,
)

# The Census encodes "no value" as large negative sentinels rather than null:
# -666666666  estimate not computable (too few samples)
# -999999999  value unavailable
# -888888888  not applicable
# -555555555  estimate is capped at a bound
# -222222222 / -333333333  suppressed for reliability
# Treating them as numbers would put "-666666666 residents" on the map.
CENSUS_NULL_SENTINELS: frozenset[float] = frozenset(
    {
        -111111111.0,
        -222222222.0,
        -333333333.0,
        -444444444.0,
        -555555555.0,
        -666666666.0,
        -777777777.0,
        -888888888.0,
        -999999999.0,
    }
)


@dataclass(frozen=True)
class MetricRecord:
    """One computed metric, carrying the evidence needed to cite it."""

    metric_key: str
    value: float | None
    unit: str
    description: str
    source_variable: str


@dataclass(frozen=True)
class GeographyRecord:
    """One geography parsed out of a Census response row."""

    geoid: str
    name: str
    geography_type: str
    state_fips: str | None
    county_fips: str | None
    tract_code: str | None


def parse_value(raw: str | None) -> float | None:
    """Convert a raw Census cell to a float, or ``None`` if unusable.

    Returns ``None`` for missing values, blank strings, non-numeric text and
    the Census's negative sentinels. A missing measurement must stay missing:
    coercing it to zero would read as a real count of nobody.
    """
    if raw is None:
        return None
    text = str(raw).strip()
    if not text or text.lower() in {"null", "none", "na", "n/a"}:
        return None
    try:
        value = float(text)
    except (TypeError, ValueError):
        return None
    if value in CENSUS_NULL_SENTINELS:
        return None
    # No metric in our catalogue can legitimately be negative (counts,
    # medians of income and age, and shares are all non-negative), so a
    # negative value here is an unrecognised annotation.
    if value < 0:
        return None
    return value


def _sum_or_none(row: dict[str, str], variable_ids: tuple[str, ...]) -> float | None:
    """Sum variables, returning ``None`` if any component is missing.

    Strict on purpose: a partial sum is a wrong number presented with the
    same confidence as a right one. Better to report the metric as
    unavailable.
    """
    total = 0.0
    for variable_id in variable_ids:
        value = parse_value(row.get(variable_id))
        if value is None:
            return None
        total += value
    return total


def compute_metric(spec: MetricSpec, row: dict[str, str]) -> MetricRecord:
    """Evaluate one metric specification against one Census row."""
    value: float | None

    if spec.kind == "direct":
        value = parse_value(row.get(spec.variable_ids[0]))
    elif spec.kind == "sum":
        value = _sum_or_none(row, spec.variable_ids)
    elif spec.kind == "difference":
        base = _sum_or_none(row, spec.variable_ids)
        subtract = _sum_or_none(row, spec.subtract_ids)
        value = None if base is None or subtract is None else max(base - subtract, 0.0)
    else:  # "share"
        numerator = _sum_or_none(row, spec.variable_ids)
        if numerator is not None and spec.subtract_ids:
            subtract = _sum_or_none(row, spec.subtract_ids)
            numerator = None if subtract is None else max(numerator - subtract, 0.0)
        denominator = (
            parse_value(row.get(spec.denominator_id)) if spec.denominator_id else None
        )
        if numerator is None or not denominator:
            # A zero denominator is a real case: a tract with no workers has
            # no commute share. Undefined, not zero.
            value = None
        else:
            value = round(numerator / denominator * 100, 2)

    return MetricRecord(
        metric_key=spec.metric_key,
        value=value,
        unit=spec.unit,
        description=spec.description,
        source_variable=spec.source_variable,
    )


def compute_metrics(row: dict[str, str]) -> list[MetricRecord]:
    """Evaluate every metric in the catalogue against one Census row."""
    return [compute_metric(spec, row) for spec in METRIC_SPECS]


def parse_geography(row: dict[str, str]) -> GeographyRecord:
    """Derive a geography from the identifier columns of a Census row.

    The Census returns hierarchy components as separate columns; the GEOID is
    their concatenation in hierarchy order, which is the identifier used to
    join against published Census products.
    """
    state = row.get("state")
    county = row.get("county")
    tract = row.get("tract")
    name = row.get("NAME", "").strip()

    if tract:
        return GeographyRecord(
            geoid=f"{state}{county}{tract}",
            name=name or f"Census Tract {tract}",
            geography_type="tract",
            state_fips=state,
            county_fips=county,
            tract_code=tract,
        )
    if county:
        return GeographyRecord(
            geoid=f"{state}{county}",
            name=name or f"County {county}",
            geography_type="county",
            state_fips=state,
            county_fips=county,
            tract_code=None,
        )
    return GeographyRecord(
        geoid=f"{state}",
        name=name or f"State {state}",
        geography_type="state",
        state_fips=state,
        county_fips=None,
        tract_code=None,
    )
