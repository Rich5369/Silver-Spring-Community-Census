"""Target geographies for Census ingestion.

Montgomery County, Maryland is FIPS state ``24``, county ``031``. Silver
Spring and Fenton Village sit inside it.

Geographic selection TODO
-------------------------
Fenton Village is a commercial district, **not a Census geography**. It has no
GEOID and no published ACS estimates. Narrowing county-wide tracts down to the
tracts covering Fenton Village needs a real spatial step:

1. Obtain the Fenton Village boundary (Montgomery County open data, or a
   hand-drawn polygon reviewed by someone who knows the district).
2. Obtain tract boundaries from the Census TIGER/Line cartographic
   boundary files for the matching vintage.
3. Intersect the two, and decide an inclusion rule - tracts that intersect at
   all, tracts whose centroid falls inside, or an area-weighted blend.

That is a genuine GIS task with real methodology choices, and guessing a
tract list here would fabricate precision the data does not have. So this
module ingests **the county and every tract within it**, which is correct,
complete and citable. Selecting and documenting the Fenton Village subset is
deliberately left as a separate, explicit step.

Whatever rule is chosen must be recorded as provenance alongside any
neighbourhood-level figure, because a Fenton Village number will be an
approximation assembled from tracts rather than a published estimate.
"""

from __future__ import annotations

from app.integrations.census.client import GeographyQuery

MARYLAND_STATE_FIPS: str = "24"
MONTGOMERY_COUNTY_FIPS: str = "031"

#: Montgomery County as a whole. Useful as a comparison baseline: a business
#: owner wants to know how their block differs from the county around it.
MONTGOMERY_COUNTY: GeographyQuery = GeographyQuery(
    for_clause=f"county:{MONTGOMERY_COUNTY_FIPS}",
    in_clause=f"state:{MARYLAND_STATE_FIPS}",
)

#: Every tract in Montgomery County. One request; the Fenton Village subset
#: is selected later, once the GIS step above exists.
MONTGOMERY_COUNTY_TRACTS: GeographyQuery = GeographyQuery(
    for_clause="tract:*",
    in_clause=f"state:{MARYLAND_STATE_FIPS} county:{MONTGOMERY_COUNTY_FIPS}",
)

INGESTION_TARGETS: tuple[tuple[str, GeographyQuery], ...] = (
    ("Montgomery County", MONTGOMERY_COUNTY),
    ("Montgomery County tracts", MONTGOMERY_COUNTY_TRACTS),
)
