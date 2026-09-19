import { mockBusinesses } from '../data/mockBusinesses';

const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim();
export const isApiConfigured = Boolean(configuredBaseUrl);
const API_BASE_URL = configuredBaseUrl?.replace(/\/$/, '') ?? '';

// The frontend consumes the versioned API contract.
const ENDPOINTS = {
  businesses: '/api/v1/businesses',
  communityProfile: '/api/v1/insights/fenton-village',
  communityMap: '/api/v1/map/community',
};

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
      sourceIds: Array.isArray(business.sourceIds) ? business.sourceIds.map(String) : [],
    }];
  });

  if (normalized.length !== records.length) throw malformedResponse('businesses');
  return normalized;
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

export function normalizeCommunityProfile(payload, requestedArea = 'Selected community') {
  // The v1 insights response is the authoritative, evidence-backed headline
  // payload. Keep the UI's small profile shape as a view-model adapter.
  if (payload?.community_snapshot) {
    const values = Object.fromEntries(payload.community_snapshot.map((item) => [item.key, item]));
    const statValue = (key) => values[key]?.value ?? null;
    const sources = payload.community_snapshot.flatMap((item) => item.evidence ?? []).map((evidence, index) => ({
      id: `${evidence.organization}-${evidence.dataset}-${index}`,
      organization: evidence.organization,
      dataset: evidence.dataset,
      year: evidence.dataset_year ?? '',
      geography: payload.study_area?.name ?? requestedArea,
      table: evidence.source_variable ?? '',
      url: evidence.source_url,
    }));
    return {
      areaName: payload.study_area?.name || requestedArea,
      dataStatus: 'Connected ACS and OpenStreetMap data',
      summary: payload.study_area?.method || 'Deterministic summary of stored community data.',
      statistics: {
        population: statValue('total_population'),
        medianHouseholdIncome: statValue('median_household_income'),
        businessCount: payload.business_landscape?.total_businesses ?? null,
      },
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
  const stat = (id, label, value) => ({
    id,
    label,
    value,
    note: 'Backend response',
    sourceIds: Array.isArray(statisticSources[id]) ? statisticSources[id].map(String) : [],
  });
  const languageValue = finiteNumber(language.value);

  return {
    areaName: String(profile.areaName || requestedArea),
    dataStatus: String(profile.dataStatus || 'Connected data — verification status not provided'),
    summary: String(profile.summary || 'Community summary not provided.'),
    stats: [
      stat('population', 'Population', formatInteger(finiteNumber(statistics.population))),
      stat('income', 'Median household income', formatCurrency(finiteNumber(statistics.medianHouseholdIncome))),
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
    sources: Array.isArray(profile.sources) ? profile.sources : [],
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

export async function getBusinesses(options = {}) {
  if (!isApiConfigured) return mockBusinesses;
  return normalizeBusinesses(await requestJson(ENDPOINTS.businesses, options));
}

export async function getCommunityProfile(area, options = {}) {
  if (!isApiConfigured) return null;
  return normalizeCommunityProfile(await requestJson(ENDPOINTS.communityProfile, options), area);
}

export async function getSources(area, options = {}) {
  if (!isApiConfigured) return [];
  return [];
}

export async function getCommunityMap(options = {}) {
  if (!isApiConfigured) return { businesses: [], communityGeoJson: null };
  const payload = await requestJson(ENDPOINTS.communityMap, options);
  const features = payload?.businesses?.features;
  if (!Array.isArray(features) || !payload?.areas) throw malformedResponse('community map');
  return {
    businesses: normalizeBusinesses(features.map(({ properties = {}, geometry = {} }) => ({
      ...properties,
      latitude: geometry.coordinates?.[1],
      longitude: geometry.coordinates?.[0],
    }))),
    communityGeoJson: payload.areas,
  };
}

export async function getTransit(options = {}) {
  if (!isApiConfigured) return [];
  const payload = await requestJson(ENDPOINTS.transit, options);
  const records = Array.isArray(payload) ? payload : payload?.transit;
  if (payload == null) return [];
  if (!Array.isArray(records)) throw malformedResponse('transit');
  return records;
}
