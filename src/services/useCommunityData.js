import { useEffect, useMemo, useState } from 'react';
import { buildDemoProfile, withBusinessStats } from '../data/communityInsights';
import { mockBusinesses } from '../data/mockBusinesses';
import { fentonVillage } from '../data/mapData';
import { findAreaFeatureContainingPoint, normalizeGeoJsonArea } from './geoJsonAdapter';
import { countBusinessesByCategory } from './businessQuery';
import {
  getBusinessCategories,
  getBusinesses,
  getCommunityMap,
  getCommunityProfile,
  isApiConfigured,
} from './api';

/**
 * The headline community profile.
 *
 * Once Census boundaries are ingested this is the real tract containing Fenton
 * Village, with its ACS metrics and full evidence. Until then it is the clearly
 * labelled demo profile. Either way the business counts reflect the records
 * actually on the map, so the panel cannot contradict the map beside it.
 */
export function resolveCommunityProfile(businesses = [], communityGeoJson = null) {
  const tract = findAreaFeatureContainingPoint(communityGeoJson, fentonVillage.position);
  if (tract) return withBusinessStats(normalizeGeoJsonArea(tract), businesses);
  return buildDemoProfile(businesses);
}

const fallbackData = {
  businesses: mockBusinesses,
  profile: buildDemoProfile(mockBusinesses),
  categories: countBusinessesByCategory(mockBusinesses),
  transit: [],
  communityGeoJson: null,
};

const loadingData = {
  businesses: [],
  profile: {
    areaName: 'Fenton Village, Silver Spring, Maryland',
    dataStatus: 'Loading connected community data',
    summary: 'Community details will appear when the data request completes.',
    stats: [],
    sources: [],
  },
  categories: [],
  transit: [],
  communityGeoJson: null,
};

/**
 * Load the community datasets, settling each request on its own.
 *
 * The four requests used to be awaited together, so the business layer - a
 * ~77KB response - waited on the ~308KB map payload before anything appeared.
 * Each now lands in its own slot and the exposed shape is recomputed from
 * whatever has arrived, so one slow response no longer holds up the rest.
 *
 * The fallback rule is unchanged and deliberate: demo records appear only
 * once the businesses request has actually failed, never while it is pending.
 */
const pendingSlot = { status: 'loading', value: null, error: null };

const initialSlots = {
  businesses: pendingSlot,
  map: pendingSlot,
  profile: pendingSlot,
  categories: pendingSlot,
};

const settledSlots = {
  businesses: { status: 'success', value: fallbackData.businesses, error: null },
  map: { status: 'success', value: null, error: null },
  profile: { status: 'success', value: fallbackData.profile, error: null },
  categories: { status: 'success', value: fallbackData.categories, error: null },
};

export function useCommunityData(area) {
  const [slots, setSlots] = useState(isApiConfigured ? initialSlots : settledSlots);

  useEffect(() => {
    if (!isApiConfigured) return undefined;

    let active = true;
    setSlots(initialSlots);

    const settle = (key, promise) => promise.then(
      (value) => { if (active) setSlots((current) => ({ ...current, [key]: { status: 'success', value, error: null } })); },
      (error) => { if (active) setSlots((current) => ({ ...current, [key]: { status: 'error', value: null, error } })); },
    );

    settle('businesses', getBusinesses());
    settle('map', getCommunityMap());
    settle('profile', getCommunityProfile(area));
    settle('categories', getBusinessCategories());

    return () => { active = false; };
  }, [area]);

  return useMemo(() => {
    const { businesses: businessSlot, map: mapSlot, profile: profileSlot, categories: categorySlot } = slots;
    const communityGeoJson = mapSlot.value?.communityGeoJson ?? null;

    // Nothing is decided until the business request resolves one way or the
    // other. Until then the UI shows its loading state rather than demo rows.
    if (businessSlot.status === 'loading') {
      return {
        status: 'loading',
        data: { ...loadingData, communityGeoJson },
        error: null,
        issue: null,
        usingFallback: false,
      };
    }

    if (businessSlot.status === 'error') {
      const profile = profileSlot.status === 'success' && profileSlot.value
        ? withBusinessStats(profileSlot.value, fallbackData.businesses)
        : resolveCommunityProfile(fallbackData.businesses, communityGeoJson);
      return {
        status: 'error',
        data: { ...fallbackData, profile, communityGeoJson },
        error: businessSlot.error,
        issue: businessSlot.error?.code === 'MALFORMED_RESPONSE' ? 'malformed' : 'api',
        usingFallback: true,
      };
    }

    // An empty successful response is authoritative. Never replace it with
    // demo rows merely to keep markers or filter chips on screen.
    const businesses = businessSlot.value;
    const profileFailed = profileSlot.status === 'error' || !profileSlot.value;

    // The backend serves the evidence-backed profile, so it is authoritative.
    // Deriving one from the tract under Fenton Village is only the fallback
    // for when that endpoint is unavailable. Either way its business counts
    // come from `businesses` above - the same array the map, the list and
    // the filter chips read - so no panel can contradict another.
    const profile = profileSlot.status === 'loading'
      ? loadingData.profile
      : profileFailed
        ? resolveCommunityProfile(businesses, communityGeoJson)
        : withBusinessStats(
          { ...profileSlot.value, sources: profileSlot.value.sources ?? [] },
          businesses,
        );

    const degradedError = [mapSlot, profileSlot, categorySlot]
      .find(({ status }) => status === 'error')?.error ?? null;

    return {
      status: degradedError ? 'partial' : 'success',
      data: {
        businesses,
        profile,
        // Counting the records we did load keeps every filter chip usable.
        categories: businesses.length === 0
          ? []
          : categorySlot.status === 'success'
            ? categorySlot.value
            : categorySlot.status === 'error'
              ? countBusinessesByCategory(businesses)
              : [],
        transit: [],
        communityGeoJson,
      },
      error: degradedError,
      issue: degradedError
        ? (degradedError.code === 'MALFORMED_RESPONSE' ? 'malformed' : 'api')
        : null,
      // A request still in flight is not a failure, so nothing is reported as
      // degraded until it settles.
      usingFallback: false,
    };
  }, [slots]);
}
