"""Normalise raw OpenStreetMap tags into our business taxonomy.

The category vocabulary is **not ours to choose**. The frontend filters on
exact string equality against a hardcoded list in
``src/services/businessQuery.js``::

    restaurants: ['Restaurant', 'Cafe', 'Bakery']
    retail:      ['Retail', 'Grocery', 'Florist']
    services:    ['Health Services', 'Personal Care', 'Pet Services',
                  'Technology Services', 'Professional Services']
    community:   ['Bike Shop']

A category we emit that is not in that list silently disappears from every
filter chip - no error, no warning, just an empty result. So the values below
are copied from the frontend, and a test asserts they still match.
"""

from __future__ import annotations

from typing import Final

# --- The taxonomy, mirroring the frontend's vocabulary ----------------------

RESTAURANT: Final = "Restaurant"
CAFE: Final = "Cafe"
BAKERY: Final = "Bakery"
RETAIL: Final = "Retail"
GROCERY: Final = "Grocery"
FLORIST: Final = "Florist"
HEALTH_SERVICES: Final = "Health Services"
PERSONAL_CARE: Final = "Personal Care"
PET_SERVICES: Final = "Pet Services"
TECHNOLOGY_SERVICES: Final = "Technology Services"
PROFESSIONAL_SERVICES: Final = "Professional Services"
BIKE_SHOP: Final = "Bike Shop"

#: Fallback for a POI we keep but cannot confidently classify. Not in the
#: frontend's filter groups, so it shows under "All Businesses" only.
UNCATEGORIZED: Final = "Uncategorized"

BUSINESS_CATEGORIES: Final[frozenset[str]] = frozenset(
    {
        RESTAURANT,
        CAFE,
        BAKERY,
        RETAIL,
        GROCERY,
        FLORIST,
        HEALTH_SERVICES,
        PERSONAL_CARE,
        PET_SERVICES,
        TECHNOLOGY_SERVICES,
        PROFESSIONAL_SERVICES,
        BIKE_SHOP,
    }
)


# --- Tag mappings -----------------------------------------------------------
# Checked in order of specificity: a more specific tag wins over a generic
# one, so shop=bakery becomes Bakery rather than the catch-all Retail.

_AMENITY: Final[dict[str, str]] = {
    "restaurant": RESTAURANT,
    "fast_food": RESTAURANT,
    "food_court": RESTAURANT,
    "ice_cream": CAFE,
    "cafe": CAFE,
    "bar": RESTAURANT,
    "pub": RESTAURANT,
    "biergarten": RESTAURANT,
    "pharmacy": HEALTH_SERVICES,
    "doctors": HEALTH_SERVICES,
    "dentist": HEALTH_SERVICES,
    "clinic": HEALTH_SERVICES,
    "hospital": HEALTH_SERVICES,
    "optician": HEALTH_SERVICES,
    "veterinary": PET_SERVICES,
    "bank": PROFESSIONAL_SERVICES,
    "post_office": PROFESSIONAL_SERVICES,
    "bureau_de_change": PROFESSIONAL_SERVICES,
    "internet_cafe": TECHNOLOGY_SERVICES,
    "spa": PERSONAL_CARE,
    "bicycle_repair_station": BIKE_SHOP,
}

_SHOP: Final[dict[str, str]] = {
    # Food and drink
    "bakery": BAKERY,
    "pastry": BAKERY,
    "coffee": CAFE,
    "tea": CAFE,
    "supermarket": GROCERY,
    "grocery": GROCERY,
    "convenience": GROCERY,
    "greengrocer": GROCERY,
    "butcher": GROCERY,
    "seafood": GROCERY,
    "deli": GROCERY,
    "farm": GROCERY,
    "alcohol": GROCERY,
    "beverages": GROCERY,
    "wine": GROCERY,
    "health_food": GROCERY,
    # Florist
    "florist": FLORIST,
    "garden_centre": FLORIST,
    # Bicycle
    "bicycle": BIKE_SHOP,
    # Health
    "chemist": HEALTH_SERVICES,
    "optician": HEALTH_SERVICES,
    "hearing_aids": HEALTH_SERVICES,
    "medical_supply": HEALTH_SERVICES,
    # Personal care
    "hairdresser": PERSONAL_CARE,
    "beauty": PERSONAL_CARE,
    "cosmetics": PERSONAL_CARE,
    "massage": PERSONAL_CARE,
    "nail_salon": PERSONAL_CARE,
    "barber": PERSONAL_CARE,
    "tattoo": PERSONAL_CARE,
    "hairdresser_supply": PERSONAL_CARE,
    # Pets
    "pet": PET_SERVICES,
    "pet_grooming": PET_SERVICES,
    "pets": PET_SERVICES,
    # Technology
    "computer": TECHNOLOGY_SERVICES,
    "mobile_phone": TECHNOLOGY_SERVICES,
    "electronics": TECHNOLOGY_SERVICES,
    "hifi": TECHNOLOGY_SERVICES,
    "telecommunication": TECHNOLOGY_SERVICES,
    "video_games": TECHNOLOGY_SERVICES,
    # Professional services
    "copyshop": PROFESSIONAL_SERVICES,
    "laundry": PROFESSIONAL_SERVICES,
    "dry_cleaning": PROFESSIONAL_SERVICES,
    "travel_agency": PROFESSIONAL_SERVICES,
    "insurance": PROFESSIONAL_SERVICES,
    "estate_agent": PROFESSIONAL_SERVICES,
    "funeral_directors": PROFESSIONAL_SERVICES,
    "money_lender": PROFESSIONAL_SERVICES,
    "storage_rental": PROFESSIONAL_SERVICES,
}

_CRAFT: Final[dict[str, str]] = {
    "bakery": BAKERY,
    "electronics_repair": TECHNOLOGY_SERVICES,
    "computer_repair": TECHNOLOGY_SERVICES,
    "photographer": PROFESSIONAL_SERVICES,
    "tailor": PROFESSIONAL_SERVICES,
    "shoemaker": PROFESSIONAL_SERVICES,
    "jeweller": RETAIL,
}

_HEALTHCARE: Final[dict[str, str]] = {
    "pharmacy": HEALTH_SERVICES,
    "doctor": HEALTH_SERVICES,
    "dentist": HEALTH_SERVICES,
    "clinic": HEALTH_SERVICES,
    "physiotherapist": HEALTH_SERVICES,
    "optometrist": HEALTH_SERVICES,
    "alternative": HEALTH_SERVICES,
    "psychotherapist": HEALTH_SERVICES,
}

#: OSM keys that mark a POI as a business at all. A POI carrying none of
#: these is not an establishment and is discarded.
BUSINESS_KEYS: Final[tuple[str, ...]] = (
    "shop",
    "amenity",
    "craft",
    "healthcare",
    "office",
)


def classify(tags: dict[str, str]) -> tuple[str, str | None]:
    """Map OSM tags to a taxonomy category.

    Returns the category plus the ``key=value`` tag that determined it, kept
    as evidence so a surprising classification can be traced back to the tag
    that caused it.

    Resilient to missing tags: an empty or unrecognised tag set yields
    ``Uncategorized`` rather than raising.
    """
    if not tags:
        return UNCATEGORIZED, None

    # Most specific first.
    for key, mapping in (
        ("shop", _SHOP),
        ("amenity", _AMENITY),
        ("craft", _CRAFT),
        ("healthcare", _HEALTHCARE),
    ):
        value = tags.get(key)
        if value and value in mapping:
            return mapping[value], f"{key}={value}"

    # Generic fallbacks: a shop we have no specific rule for is still retail,
    # and any office is a professional service.
    if tags.get("shop"):
        return RETAIL, f"shop={tags['shop']}"
    if tags.get("office"):
        return PROFESSIONAL_SERVICES, f"office={tags['office']}"

    return UNCATEGORIZED, None


def is_business(tags: dict[str, str]) -> bool:
    """Whether a POI looks like a business establishment.

    Excludes the many non-commercial things that carry ``amenity``: benches,
    waste baskets, parking, drinking fountains and so on.
    """
    if not tags:
        return False
    if not any(tags.get(key) for key in BUSINESS_KEYS):
        return False
    category, _ = classify(tags)
    # An unclassifiable amenity (bench, parking, toilets) is not a business;
    # an unclassifiable *shop* still is, and classify() already returns
    # Retail for that case.
    return category != UNCATEGORIZED
