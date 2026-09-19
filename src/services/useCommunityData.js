import { useEffect, useState } from 'react';
import { buildDemoProfile, withBusinessStats } from '../data/communityInsights';
import { mockBusinesses } from '../data/mockBusinesses';
import { fentonVillage } from '../data/mapData';
import { findAreaFeatureContainingPoint, normalizeGeoJsonArea } from './geoJsonAdapter';
import { countBusinessesByCategory } from './businessQuery';
import {
  getBusinessCategories,
  getCommunityMap,
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

export function useCommunityData() {
  const [state, setState] = useState({
    status: isApiConfigured ? 'loading' : 'success',
    data: fallbackData,
    error: null,
    issue: null,
    usingFallback: !isApiConfigured,
  });

  useEffect(() => {
    if (!isApiConfigured) return undefined;

    const controller = new AbortController();
    const options = { signal: controller.signal };
    setState((current) => ({ ...current, status: 'loading', error: null, issue: null }));

    // The map is required; the category vocabulary is an enhancement. Settle
    // both so a categories outage degrades the filter chips rather than
    // dropping the whole app back to demo data.
    Promise.allSettled([getCommunityMap(options), getBusinessCategories(options)])
      .then(([mapResult, categoriesResult]) => {
        if (controller.signal.aborted) return;
        if (mapResult.status === 'rejected') throw mapResult.reason;

        const communityMap = mapResult.value;
        const categoriesFailed = categoriesResult.status === 'rejected';
        const categoriesError = categoriesFailed ? categoriesResult.reason : null;

        setState({
          status: categoriesFailed ? 'partial' : 'success',
          data: {
            businesses: communityMap.businesses,
            profile: resolveCommunityProfile(
              communityMap.businesses,
              communityMap.communityGeoJson,
            ),
            // Counting the records we did load keeps every filter chip usable.
            categories: categoriesFailed
              ? countBusinessesByCategory(communityMap.businesses)
              : categoriesResult.value,
            transit: [],
            communityGeoJson: communityMap.communityGeoJson,
          },
          error: categoriesError,
          issue: categoriesFailed
            ? (categoriesError?.code === 'MALFORMED_RESPONSE' ? 'malformed' : 'api')
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
  }, []);

  return state;
}
