import { fentonVillageInsights } from '../data/communityInsights';
import { mockBusinesses } from '../data/mockBusinesses';
import { countBusinessesByCategory } from './businessQuery';

const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim();
// The frontend and API are deployed together in the demo image, and Vite
// proxies /api locally. An unset URL must therefore mean same-origin API,
// not silent mock-data mode.
export const isApiConfigured = true;
const API_BASE_URL = configuredBaseUrl?.replace(/\/$/, '') ?? '';

// Keep finalized backend paths centralized so versioning remains explicit.
const ENDPOINTS = {
  businesses: '/api/v1/businesses',
  businessCategories: '/api/v1/businesses/categories',
  communityMap: '/api/v1/map/community',
  communityProfile: '/api/v1/insights/fenton-village',
  query: '/api/v1/query',
  governmentSummary: '/api/v1/government/summary',
};

/**
 * In-flight and resolved GET responses, keyed by path.
 *
 * Every dataset here is read-only for the life of the page, so a second caller
 * joins the first request instead of issuing its own. The shared promise is
 * deliberately not tied to any one caller's abort signal: a consumer that goes
 * away must not cancel a request another consumer is still waiting on, and an
 * aborted fetch surfacing as a rejection would drop the app to demo data.
 * Consumers still guard their own `setState` with their own abort flag.
 *
 * Rejections are evicted so a failed request can be retried; successes are
 * kept for the session.
 */
const sharedRequests = new Map();

function sharedJson(path) {
  if (!sharedRequests.has(path)) {
    sharedRequests.set(path, requestJson(path).catch((error) => {
      sharedRequests.delete(path);
      throw error;
    }));
  }
  return sharedRequests.get(path);
}

async function requestJson(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: { Accept: 'application/json', ...options.headers },
  });

  if (!response.ok) {
    throw new Error(`Community data request failed (${response.status})`);
  }

  if (response.status === 204) return null;
  return response.json();
}

export async function getGovernmentSummary() {
  return sharedJson(ENDPOINTS.governmentSummary);
}

export async function getGovernmentTrends() {
  return sharedJson('/api/v1/government/trends');
}

export async function getGovernmentServiceRequests() {
  return sharedJson('/api/v1/government/service-requests');
}

function malformedResponse(resource) {
  const error = new Error(`Malformed ${resource} response`);
  error.name = 'MalformedResponseError';
  error.code = 'MALFORMED_RESPONSE';
  return error;
}

const finiteNumber = (value) => {
  if (value === null || value === undefined || value === '') return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
};

export function normalizeBusinesses(payload) {
  const records = Array.isArray(payload) ? payload : payload?.businesses;
  if (payload == null) return [];
  if (!Array.isArray(records)) throw malformedResponse('businesses');

  const normalized = records.flatMap((business, index) => {
    const latitude = finiteNumber(business?.latitude);
    const longitude = finiteNumber(business?.longitude);
    if (!business?.name || latitude === null || longitude === null) return [];

    return [{
      id: business.id ?? `business-${index}`,
      name: String(business.name),
      category: String(business.category || 'Uncategorized'),
      latitude,
      longitude,
      address: String(business.address || 'Address not provided'),
      source: String(business.source || 'Source not provided'),
      sourceUrl: String(business.source_url || business.sourceUrl || ''),
      dataset: String(business.dataset || 'Business record'),
      sourceIds: Array.isArray(business.sourceIds) ? business.sourceIds.map(String) : [],
    }];
  });

  if (normalized.length !== records.length) throw malformedResponse('businesses');
  return normalized;
}

function normalizeMapBusinesses(featureCollection) {
  if (featureCollection?.type !== 'FeatureCollection' || !Array.isArray(featureCollection.features)) {
    throw malformedResponse('community map businesses');
  }

  const records = featureCollection.features.map((feature) => {
    const coordinates = feature?.geometry?.coordinates;
    const properties = feature?.properties ?? {};
    const business = properties.business ?? {};

    return {
      id: business.id ?? feature?.id,
      name: properties.name,
      category: business.category,
      latitude: Array.isArray(coordinates) ? coordinates[1] : null,
      longitude: Array.isArray(coordinates) ? coordinates[0] : null,
      address: business.address,
      source: business.source,
      source_url: business.source_url,
      // Whatever dataset the map payload carries, if it ever carries one. It
      // does not today, and naming a provider here would put an invented string
      // in front of the user as provenance. normalizeBusinesses falls back to a
      // neutral "Business record" instead. GET /api/v1/businesses reports the
      // real dataset, which is why that endpoint feeds the business layer.
      dataset: business.dataset,
    };
  });

  return normalizeBusinesses({ businesses: records });
}

/**
 * Category counts from GET /api/v1/businesses/categories.
 *
 * The backend builds this from stored rows, so every category listed has at
 * least one business behind it - it is the authoritative vocabulary for filter
 * controls, including categories the frontend has never seen before.
 */
export function normalizeBusinessCategories(payload) {
  const records = Array.isArray(payload) ? payload : payload?.categories;
  if (payload == null) return [];
  if (!Array.isArray(records)) throw malformedResponse('business categories');

  const normalized = records.flatMap((record) => {
    const category = typeof record?.category === 'string' ? record.category.trim() : '';
    const count = finiteNumber(record?.count);
    if (!category || count === null || count < 0) return [];
    return [{ category, count: Math.trunc(count) }];
  });

  if (normalized.length !== records.length) throw malformedResponse('business categories');
  return normalized;
}

/**
 * @param {object} payload            GET /api/v1/map/community
 * @param {object} [options]
 * @param {boolean} [options.includeBusinesses]
 *   The map payload repeats the whole business layer that GET
 *   /api/v1/businesses already serves, and the app reads the records from that
 *   endpoint instead - it is the one record of truth for the business layer.
 *   Normalizing the repeated copy only to discard it costs a few hundred
 *   kilobytes of parsing on the main thread during load, so the app opts out
 *   and takes the areas alone. Callers that want the records (the data
 *   pipeline check) get them by leaving this true.
 */
export function normalizeCommunityMap(payload, { includeBusinesses = true } = {}) {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    throw malformedResponse('community map');
  }
  if (payload.areas?.type !== 'FeatureCollection' || !Array.isArray(payload.areas.features)) {
    throw malformedResponse('community map areas');
  }

  return {
    businesses: includeBusinesses ? normalizeMapBusinesses(payload.businesses) : [],
    communityGeoJson: payload.areas,
  };
}

const formatInteger = (value) => (
  value === null
    ? 'Data unavailable'
    : new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(value)
);

const formatCurrency = (value) => (
  value === null
    ? 'Data unavailable'
    : new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(value)
);

// The snapshot carries fifteen metrics and the panel shows a headline set of
// them beside the business counts. Add a key here to surface another; one the
// backend marks unavailable is skipped rather than rendered as an empty card.
// `range` keys read from payload.ranges - those are values the backend declines
// to collapse into a single number, such as a district median household income,
// which cannot be derived from tract medians because medians are not additive.
const HEADLINE_COMMUNITY_METRICS = [
  { source: 'metric', key: 'total_population' },
  { source: 'range', key: 'median_household_income' },
  { source: 'metric', key: 'multilingual_household_share' },
];

// Planning Trends renders these as accordions of their own. GET
// /government/trends carries population, renter share and income only, so the
// snapshot is the sole frontend-reachable source for these two: they arrive as
// a current value with its evidence and no historical series behind them.
const TREND_INDICATOR_KEYS = ['rent_burden_share', 'unemployment_rate'];

/** Current value plus provenance for each indicator the snapshot supports. */
const buildTrendIndicators = (values) => Object.fromEntries(
  TREND_INDICATOR_KEYS.flatMap((key) => {
    const item = values[key];
    const value = finiteNumber(item?.value);
    if (!item?.available || value === null) return [];
    // A record without a release year cannot be cited as one, so it is dropped
    // rather than shown with an invented or blank vintage.
    const evidence = (item.evidence ?? []).flatMap((record) => (
      record?.dataset_year == null ? [] : [{
        organization: String(record.organization || ''),
        dataset: String(record.dataset || ''),
        year: Number(record.dataset_year),
        variable: String(record.source_variable || ''),
        url: String(record.source_url || ''),
      }]
    ));
    return [[key, {
      key,
      label: String(item.label || key),
      value,
      unit: String(item.unit || ''),
      formula: String(item.derivation?.formula || ''),
      tractCount: finiteNumber(item.coverage?.tracts_with_data) ?? 0,
      evidence,
    }]];
  }),
);

const formatMetricValue = (value, unit) => {
  if (value === null || value === undefined) return 'Data unavailable';
  if (unit === 'percent') {
    return `${new Intl.NumberFormat('en-US', { maximumFractionDigits: 1 }).format(value)}%`;
  }
  if (unit === 'usd' || unit === 'dollars') return formatCurrency(value);
  return formatInteger(value);
};

export function normalizeCommunityProfile(payload, requestedArea = 'Selected community') {
  if (payload?.community_snapshot) {
    const values = Object.fromEntries(payload.community_snapshot.map((item) => [item.key, item]));
    const ranges = Object.fromEntries((payload.ranges ?? []).map((item) => [item.key, item]));

    // Evidence is keyed by what it cites rather than by its position in the
    // payload, so the many metrics drawn from one ACS release collapse into a
    // single source card and each stat can point at exactly the records behind
    // it. Indexing by position produced a near-duplicate source per metric.
    const sources = [];
    const cite = (item) => (item?.evidence ?? []).map((evidence) => {
      const id = `${evidence.organization}-${evidence.dataset}-${evidence.source_variable ?? 'summary'}`;
      if (!sources.some((source) => source.id === id)) {
        sources.push({
          id,
          organization: evidence.organization,
          dataset: evidence.dataset,
          year: evidence.dataset_year ?? '',
          geography: payload.study_area?.name ?? requestedArea,
          table: evidence.source_variable ?? '',
          url: evidence.source_url,
        });
      }
      return id;
    });

    // These are the cards the panel renders. They were previously returned under
    // a `statistics` object that nothing read, so every Census value the backend
    // served was dropped before it reached the UI.
    const stats = HEADLINE_COMMUNITY_METRICS.flatMap(({ source, key }) => {
      const item = source === 'range' ? ranges[key] : values[key];
      if (!item?.available) return [];
      const value = source === 'range'
        ? `${formatMetricValue(item.minimum, item.unit)} – ${formatMetricValue(item.maximum, item.unit)}`
        : formatMetricValue(item.value, item.unit);
      const note = source === 'range'
        ? `Range across ${item.coverage?.tracts_with_data ?? 0} tracts`
        : 'US Census Bureau ACS';
      return [{
        id: key,
        label: item.label,
        value,
        rawValue: source === 'metric' ? finiteNumber(item.value) : null,
        note,
        sourceIds: cite(item),
      }];
    });

    return {
      areaName: payload.study_area?.name || requestedArea,
      dataStatus: 'Connected ACS and OpenStreetMap data',
      summary: payload.study_area?.method || 'Deterministic summary of stored community data.',
      stats,
      indicators: buildTrendIndicators(values),
      opportunityMetrics: Object.fromEntries(
        ['young_adult_share', 'commute_active_share', 'renter_share'].flatMap((key) => {
          const item = values[key];
          return item?.available ? [[key, { label: item.label, value: item.value, unit: item.unit }]] : [];
        }),
      ),
      sources,
    };
  }
  const profile = payload?.profile ?? payload;
  if (payload == null || payload?.profile === null) {
    return {
      areaName: requestedArea,
      dataStatus: 'No profile data available',
      summary: 'The backend returned no community profile for this area.',
      stats: [],
      indicators: {},
      sources: [],
    };
  }
  if (!profile || typeof profile !== 'object' || Array.isArray(profile)) {
    throw malformedResponse('community profile');
  }
  const knownFields = ['areaName', 'summary', 'dataStatus', 'statistics', 'statisticSources'];
  if (!knownFields.some((field) => Object.hasOwn(profile, field))) {
    throw malformedResponse('community profile');
  }
  if (profile.statistics != null && typeof profile.statistics !== 'object') {
    throw malformedResponse('community profile');
  }

  const statistics = profile.statistics ?? {};
  const language = statistics.language ?? {};
  const statisticSources = profile.statisticSources ?? {};
  const stat = (id, label, value, rawValue = null) => ({
    id,
    label,
    value,
    rawValue,
    note: 'Backend response',
    sourceIds: Array.isArray(statisticSources[id]) ? statisticSources[id].map(String) : [],
  });
  const languageValue = finiteNumber(language.value);

  return {
    areaName: String(profile.areaName || requestedArea),
    dataStatus: String(profile.dataStatus || 'Connected data — verification status not provided'),
    summary: String(profile.summary || 'Community summary not provided.'),
    stats: [
      stat('population', 'Population', formatInteger(finiteNumber(statistics.population)), finiteNumber(statistics.population)),
      stat('income', 'Median household income', formatCurrency(finiteNumber(statistics.medianHouseholdIncome)), finiteNumber(statistics.medianHouseholdIncome)),
      stat(
        'language',
        String(language.label || 'Language statistic'),
        languageValue === null
          ? 'Data unavailable'
          : `${formatInteger(languageValue)}${language.unit === 'percent' ? '%' : ''}`,
      ),
      stat('businesses', 'Businesses shown', formatInteger(finiteNumber(statistics.businessCount))),
      stat('restaurants', 'Restaurants', formatInteger(finiteNumber(statistics.restaurantCount))),
      stat('retail', 'Retail', formatInteger(finiteNumber(statistics.retailCount))),
    ],
    indicators: {},
    sources: [],
  };
}

export function normalizeSources(payload) {
  const records = Array.isArray(payload) ? payload : payload?.sources;
  if (payload == null) return [];
  if (!Array.isArray(records)) throw malformedResponse('sources');
  if (records.some((source) => !source || typeof source !== 'object' || Array.isArray(source))) {
    throw malformedResponse('sources');
  }

  return records.map((source) => ({
    id: source?.id == null ? '' : String(source.id),
    organization: String(source?.organization || ''),
    dataset: String(source?.dataset || ''),
    year: String(source?.year || ''),
    geography: String(source?.geography || ''),
    table: String(source?.table || ''),
    url: String(source?.url || ''),
  }));
}

export async function getBusinesses() {
  if (!isApiConfigured) return mockBusinesses;
  return normalizeBusinesses(await sharedJson(ENDPOINTS.businesses));
}

export async function getBusinessCategories() {
  if (!isApiConfigured) return countBusinessesByCategory(mockBusinesses);
  return normalizeBusinessCategories(await sharedJson(ENDPOINTS.businessCategories));
}

export async function getCommunityMap() {
  if (!isApiConfigured) {
    return { businesses: mockBusinesses, communityGeoJson: null };
  }
  return normalizeCommunityMap(await sharedJson(ENDPOINTS.communityMap), { includeBusinesses: false });
}

export async function getCommunityProfile(area) {
  if (!isApiConfigured) return null;
  return normalizeCommunityProfile(await sharedJson(ENDPOINTS.communityProfile), area);
}

export async function askCommunityQuestion(question, options = {}) {
  if (!isApiConfigured) throw new Error('The question API is not configured.');
  return requestJson(ENDPOINTS.query, {
    ...options,
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...options.headers },
    body: JSON.stringify({ question }),
  });
}
