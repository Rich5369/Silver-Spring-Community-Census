export const businessFilters = [
  { id: 'all', label: 'All Businesses' },
  { id: 'restaurants', label: 'Restaurants' },
  { id: 'retail', label: 'Retail' },
  { id: 'services', label: 'Services' },
];

const categoryGroups = {
  restaurants: ['Restaurant', 'Cafe', 'Bakery'],
  retail: ['Retail', 'Grocery', 'Florist'],
  services: ['Health Services', 'Personal Care', 'Pet Services', 'Technology Services', 'Professional Services'],
};

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
  const allowedCategories = categoryGroups[filter];

  return businesses.filter((business) => {
    const matchesFilter = !allowedCategories || allowedCategories.includes(business.category);
    const searchableText = `${business.name} ${business.category}`.toLocaleLowerCase();
    const matchesSearch = !normalizedSearch || searchableText.includes(normalizedSearch);

    return matchesFilter && matchesSearch;
  });
}
