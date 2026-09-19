import { mockBusinesses } from './mockBusinesses';
import { areAllDemoBusinesses } from '../services/provenance';
import { countBusinessesByCategory } from '../services/businessQuery';

// How many individual categories the snapshot lists before grouping the tail.
const SNAPSHOT_CATEGORY_LIMIT = 3;

// Illustrative values only. These are clearly labelled in the UI and are
// replaced wholesale by real tract metrics once Census data is ingested.
const demoProfileBase = {
  areaName: 'Fenton Village',
  dataStatus: 'Demo profile — illustrative values only',
  summary: 'Our primary demonstration area, chosen to show how local businesses, community context, and supporting evidence can be explored together.',
  stats: [
    {
      id: 'population',
      label: 'Population',
      value: 'Demo: 8,200',
      note: 'Illustrative estimate',
      sourceIds: ['demo-community-profile'],
    },
    {
      id: 'income',
      label: 'Median household income',
      value: 'Demo: $84K',
      note: 'Illustrative estimate',
      sourceIds: ['demo-community-profile'],
    },
    {
      id: 'language',
      label: 'Multilingual households',
      value: 'Demo: 38%',
      note: 'Illustrative estimate',
      sourceIds: ['demo-community-profile'],
    },
  ],
  sources: [
    {
      id: 'demo-community-profile',
      organization: 'Demo project data',
      dataset: 'Fenton Village mock profile',
      year: 'Not applicable',
      geography: 'Illustrative Fenton Village area',
      table: 'No verified table connected',
      url: '',
    },
  ],
};

const demoBusinessSource = {
  id: 'demo-businesses',
  organization: 'Silver Spring Community Census demo',
  dataset: 'Fenton Village mock business layer',
  year: 'Demo data',
  geography: 'Illustrative Fenton Village area',
  table: 'Mock business records',
  url: '',
};

/**
 * Business statistics for whichever records are actually on the map, with a
 * source that reflects where they came from.
 *
 * The category breakdown is derived from the records rather than naming fixed
 * categories, so it describes whatever the backend actually serves instead of
 * assuming the two categories the mock layer happened to contain.
 */
export function buildBusinessStats(businesses = []) {
  const isDemo = areAllDemoBusinesses(businesses);
  // Describe the connected layer from the records themselves rather than
  // naming a provider we have not been told about.
  const sample = businesses.find((business) => business.dataset || business.sourceUrl);
  const source = isDemo ? demoBusinessSource : {
    id: 'live-businesses',
    organization: 'Connected business API',
    dataset: sample?.dataset || 'Business records',
    year: '',
    geography: 'Silver Spring study area',
    table: '',
    url: sample?.sourceUrl || '',
  };
  const note = isDemo ? 'Mock map records' : 'Mapped business records';
  const stat = (id, label, value) => ({ id, label, value: String(value), note, sourceIds: [source.id] });

  const byCategory = countBusinessesByCategory(businesses);
  const leading = byCategory.slice(0, SNAPSHOT_CATEGORY_LIMIT);
  const remainder = byCategory.slice(SNAPSHOT_CATEGORY_LIMIT);
  const remainderTotal = remainder.reduce((total, entry) => total + entry.count, 0);

  const stats = [
    stat('businesses', 'Businesses mapped', businesses.length),
    stat('categories', 'Categories represented', byCategory.length),
    ...leading.map((entry) => stat(`category-${entry.category}`, entry.category, entry.count)),
  ];
  if (remainder.length > 0) {
    stats.push(stat(
      'category-other',
      `Other categories (${remainder.length})`,
      remainderTotal,
    ));
  }

  return { source, stats };
}

/** Append live business counts to any profile, demo or real Census tract. */
export function withBusinessStats(profile, businesses = []) {
  const { stats, source } = buildBusinessStats(businesses);

  return {
    ...profile,
    stats: [...(profile.stats ?? []), ...stats],
    sources: [...(profile.sources ?? []), source],
  };
}

export function buildDemoProfile(businesses = mockBusinesses) {
  return withBusinessStats(demoProfileBase, businesses);
}

export const fentonVillageInsights = buildDemoProfile(mockBusinesses);
