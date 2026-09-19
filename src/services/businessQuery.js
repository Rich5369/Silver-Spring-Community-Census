export const businessFilterGroups = {
  restaurants: ['Restaurant', 'Cafe', 'Bakery'],
  retail: ['Retail', 'Grocery', 'Florist', 'Bike Shop'],
  services: ['Health Services', 'Personal Care', 'Pet Services', 'Technology Services', 'Professional Services'],
};

const groupLabels = {
  restaurants: 'Restaurants',
  retail: 'Retail',
  services: 'Services',
};

// Every category the curated groups above account for. Anything the backend
// serves that is not in here falls into the "Other" chip rather than becoming
// unreachable, so a new category in the data can never hide businesses.
const groupedCategories = new Set(Object.values(businessFilterGroups).flat());

export const OTHER_FILTER_ID = 'other';

const categoryOf = (business) => business?.category || 'Uncategorized';

export function isCategoryGrouped(category) {
  return groupedCategories.has(category);
}

/** Category counts for a set of records, largest first. */
export function countBusinessesByCategory(businesses = []) {
  const counts = new Map();
  businesses.forEach((business) => {
    const category = categoryOf(business);
    counts.set(category, (counts.get(category) ?? 0) + 1);
  });

  return [...counts.entries()]
    .map(([category, count]) => ({ category, count }))
    .sort((a, b) => b.count - a.count || a.category.localeCompare(b.category));
}

/** Categories the curated groups do not cover. Accepts records or {category}. */
export function findUncoveredCategories(categories = []) {
  return [...new Set(
    categories
      .map((entry) => (typeof entry === 'string' ? entry : entry?.category))
      .filter((category) => category && !groupedCategories.has(category)),
  )];
}

/**
 * Filter chips with live counts.
 *
 * Counts come from the records passed in, so a chip never promises results it
 * cannot deliver. The "Other" chip appears only when the data actually contains
 * a category outside the curated groups.
 */
export function buildBusinessFilters(businesses = [], knownCategories = []) {
  const counts = new Map(
    countBusinessesByCategory(businesses).map(({ category, count }) => [category, count]),
  );
  const sumOf = (categories) => categories.reduce(
    (total, category) => total + (counts.get(category) ?? 0), 0,
  );

  const filters = [
    { id: 'all', label: 'All Businesses', count: businesses.length },
    ...Object.entries(businessFilterGroups).map(([id, categories]) => ({
      id,
      label: groupLabels[id] ?? id,
      count: sumOf(categories),
    })),
  ];

  // Consider both what the loaded records contain and what the backend says
  // exists, so a category hidden by the current search still gets a chip.
  const uncovered = findUncoveredCategories([...counts.keys(), ...knownCategories]);
  if (uncovered.length > 0) {
    filters.push({ id: OTHER_FILTER_ID, label: 'Other', count: sumOf(uncovered) });
  }

  return filters;
}

// Single source of wording for result counts so the map, the list and the filter
// panel can never disagree about how many businesses are showing.
export function describeResultCount(count, total) {
  if (total === 0) return 'No business records loaded yet';
  if (count === 0) return `No businesses match — 0 of ${total}`;
  if (count === total) return `Showing all ${total} ${total === 1 ? 'business' : 'businesses'}`;
  return `Showing ${count} of ${total} businesses`;
}

// Local adapter: this function can later be replaced by an API or natural-language query service.
export function queryBusinesses({ businesses = [], filter = 'all', searchTerm = '' }) {
  const normalizedSearch = searchTerm.trim().toLocaleLowerCase();

  return businesses.filter((business) => {
    const category = categoryOf(business);
    let matchesFilter;
    if (filter === OTHER_FILTER_ID) matchesFilter = !groupedCategories.has(category);
    else if (businessFilterGroups[filter]) matchesFilter = businessFilterGroups[filter].includes(category);
    // 'all', and any unknown id, stay permissive rather than hiding records.
    else matchesFilter = true;

    const searchableText = `${business.name} ${category}`.toLocaleLowerCase();
    const matchesSearch = !normalizedSearch || searchableText.includes(normalizedSearch);

    return matchesFilter && matchesSearch;
  });
}
