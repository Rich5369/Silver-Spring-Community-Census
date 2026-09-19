import { fentonVillageInsights } from '../data/communityInsights';
import { mockBusinesses } from '../data/mockBusinesses';

const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim();
export const isApiConfigured = Boolean(configuredBaseUrl);
const API_BASE_URL = configuredBaseUrl?.replace(/\/$/, '') ?? '';

// Keep finalized backend paths centralized so versioning remains explicit.
const ENDPOINTS = {
  businesses: '/api/v1/businesses',
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
      dataset: 'OpenStreetMap points of interest',
    };
  });

  return normalizeBusinesses({ businesses: records });
}

export function normalizeCommunityMap(payload) {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    throw malformedResponse('community map');
  }
  if (payload.areas?.type !== 'FeatureCollection' || !Array.isArray(payload.areas.features)) {
    throw malformedResponse('community map areas');
  }

  return {
    businesses: normalizeMapBusinesses(payload.businesses),
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

export function normalizeCommunityProfile(payload, requestedArea = 'Selected community') {
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

export async function getBusinesses(options = {}) {
  if (!isApiConfigured) return mockBusinesses;
  return normalizeBusinesses(await requestJson(ENDPOINTS.businesses, options));
}

export async function getCommunityMap(options = {}) {
  if (!isApiConfigured) {
    return { businesses: mockBusinesses, communityGeoJson: null };
  }
  return normalizeCommunityMap(await requestJson(ENDPOINTS.communityMap, options));
}
