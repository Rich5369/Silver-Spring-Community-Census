import { useEffect, useState } from 'react';
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

export function useCommunityData(area) {
  const [state, setState] = useState({
    status: isApiConfigured ? 'loading' : 'success',
    data: isApiConfigured ? loadingData : fallbackData,
    error: null,
    issue: null,
    usingFallback: !isApiConfigured,
  });

  useEffect(() => {
    if (!isApiConfigured) return undefined;

    const controller = new AbortController();
    const options = { signal: controller.signal };
    setState({
      status: 'loading',
      data: loadingData,
      error: null,
      issue: null,
      usingFallback: false,
    });

    // GET /api/v1/businesses is the one required request: it is the record of
    // truth for the business layer. The tract polygons, the backend profile and
    // the category vocabulary are enhancements, so settle all four - losing one
    // degrades a single part of the UI rather than dropping the whole app back
    // to demo data.
    Promise.allSettled([
      getBusinesses(options),
      getCommunityMap(options),
      getCommunityProfile(area, options),
      getBusinessCategories(options),
    ])
      .then(([businessesResult, mapResult, profileResult, categoriesResult]) => {
        if (controller.signal.aborted) return;

        const communityMap = mapResult.status === 'fulfilled' ? mapResult.value : null;
        const businessesFailed = businessesResult.status === 'rejected';
        if (businessesFailed) {
          const fallbackProfile = profileResult.status === 'fulfilled' && profileResult.value
            ? withBusinessStats(profileResult.value, fallbackData.businesses)
            : resolveCommunityProfile(fallbackData.businesses, communityMap?.communityGeoJson ?? null);
          setState({
            status: 'error',
            data: {
              ...fallbackData,
              profile: fallbackProfile,
              communityGeoJson: communityMap?.communityGeoJson ?? null,
            },
            error: businessesResult.reason,
            issue: businessesResult.reason?.code === 'MALFORMED_RESPONSE' ? 'malformed' : 'api',
            usingFallback: true,
          });
          return;
        }
        // An empty successful response is authoritative. Never replace it with
        // demo rows merely to keep markers or filter chips on screen.
        const businesses = businessesResult.value;

        const areasFailed = mapResult.status === 'rejected';
        const profileFailed = profileResult.status === 'rejected' || !profileResult.value;
        const categoriesFailed = categoriesResult.status === 'rejected';
        const degradedError = [businessesResult, mapResult, profileResult, categoriesResult]
          .find((result) => result.status === 'rejected')?.reason ?? null;

        // The backend serves the evidence-backed profile, so it is authoritative.
        // Deriving one from the tract under Fenton Village is only the fallback
        // for when that endpoint is unavailable. Either way its business counts
        // come from `businesses` above - the same array the map, the list and
        // the filter chips read - so no panel can contradict another.
        const profile = profileFailed
          ? resolveCommunityProfile(businesses, communityMap?.communityGeoJson ?? null)
          : withBusinessStats(
            { ...profileResult.value, sources: profileResult.value.sources ?? [] },
            businesses,
          );

        setState({
          status: businessesFailed || areasFailed || profileFailed || categoriesFailed
            ? 'partial'
            : 'success',
          data: {
            businesses,
            profile,
            // Counting the records we did load keeps every filter chip usable.
            categories: businesses.length === 0
              ? []
              : categoriesFailed
              ? countBusinessesByCategory(businesses)
              : categoriesResult.value,
            transit: [],
            communityGeoJson: communityMap?.communityGeoJson ?? null,
          },
          error: degradedError,
          issue: degradedError
            ? (degradedError.code === 'MALFORMED_RESPONSE' ? 'malformed' : 'api')
            : null,
          usingFallback: false,
        });
      })
      .catch((error) => {
        // Defensive guard for unexpected errors outside individual request promises.
        if (error.name === 'AbortError') return;
        setState({
          status: 'error',
          data: fallbackData,
          error,
          issue: error.code === 'MALFORMED_RESPONSE' ? 'malformed' : 'api',
          usingFallback: true,
        });
      });

    return () => controller.abort();
  }, [area]);

  return state;
}
