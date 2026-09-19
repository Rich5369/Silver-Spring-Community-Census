import { fentonVillageInsights } from '../data/communityInsights';
import { mockBusinesses } from '../data/mockBusinesses';

const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim();
export const isApiConfigured = Boolean(configuredBaseUrl);
const API_BASE_URL = configuredBaseUrl?.replace(/\/$/, '') ?? '';

// Tentative paths are centralized here. Update only this object when the backend team
// finalizes endpoint names; these are a frontend contract proposal, not live production APIs.
const ENDPOINTS = {
  businesses: '/businesses',
  communityProfile: (area) => `/community-profiles/${encodeURIComponent(area)}`,
  sources: (area) => `/sources?area=${encodeURIComponent(area)}`,
  transit: '/transit',
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

const finiteNumber = (value) => {
  if (value === null || value === undefined || value === '') return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
};

export function normalizeBusinesses(payload) {
  const records = Array.isArray(payload) ? payload : payload?.businesses;
  if (!Array.isArray(records)) return [];

  return records.flatMap((business, index) => {
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
    }];
  });
}

const formatInteger = (value) => (
  value === null ? '—' : new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(value)
);

const formatCurrency = (value) => (
  value === null
    ? '—'
    : new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(value)
);

export function normalizeCommunityProfile(payload, requestedArea = 'Selected community') {
  const profile = payload?.profile ?? payload;
  if (!profile || typeof profile !== 'object') {
    return {
      areaName: requestedArea,
      dataStatus: 'No profile data available',
      summary: 'The backend returned no community profile for this area.',
      stats: [],
      sources: [],
    };
  }

  const statistics = profile.statistics ?? {};
  const language = statistics.language ?? {};
  const stat = (id, label, value) => ({ id, label, value, note: 'Backend response' });
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
          ? '—'
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
  if (!Array.isArray(records)) return [];

  return records.map((source) => ({
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
  if (!isApiConfigured) return fentonVillageInsights;
  return normalizeCommunityProfile(await requestJson(ENDPOINTS.communityProfile(area), options), area);
}

export async function getSources(area, options = {}) {
  if (!isApiConfigured) return fentonVillageInsights.sources;
  return normalizeSources(await requestJson(ENDPOINTS.sources(area), options));
}

export async function getTransit(options = {}) {
  if (!isApiConfigured) return [];
  const payload = await requestJson(ENDPOINTS.transit, options);
  const records = Array.isArray(payload) ? payload : payload?.transit;
  return Array.isArray(records) ? records : [];
}
