import { useEffect, useState } from 'react';
import { buildDemoProfile, withBusinessStats } from '../data/communityInsights';
import { mockBusinesses } from '../data/mockBusinesses';
import { fentonVillage } from '../data/mapData';
import { findAreaFeatureContainingPoint, normalizeGeoJsonArea } from './geoJsonAdapter';
import { countBusinessesByCategory } from './businessQuery';
import {
  getBusinessCategories,
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

export function useCommunityData(area) {
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

    // The map is required. The backend profile and the category vocabulary are
    // enhancements, so settle all three: losing either degrades one part of the
    // UI rather than dropping the whole app back to demo data.
    Promise.allSettled([
      getCommunityMap(options),
      getCommunityProfile(area, options),
      getBusinessCategories(options),
    ])
      .then(([mapResult, profileResult, categoriesResult]) => {
        if (controller.signal.aborted) return;
        if (mapResult.status === 'rejected') throw mapResult.reason;

        const communityMap = mapResult.value;
        const profileFailed = profileResult.status === 'rejected' || !profileResult.value;
        const categoriesFailed = categoriesResult.status === 'rejected';
        const degradedError = (profileResult.status === 'rejected' ? profileResult.reason : null)
          ?? (categoriesFailed ? categoriesResult.reason : null);

        // The backend serves the evidence-backed profile, so it is authoritative.
        // Deriving one from the tract under Fenton Village is only the fallback
        // for when that endpoint is unavailable. Either way the business counts
        // come from the records actually on the map, so the snapshot cannot
        // contradict the map beside it.
        const profile = profileFailed
          ? resolveCommunityProfile(communityMap.businesses, communityMap.communityGeoJson)
          : withBusinessStats(
            { ...profileResult.value, sources: profileResult.value.sources ?? [] },
            communityMap.businesses,
          );

        setState({
          status: profileFailed || categoriesFailed ? 'partial' : 'success',
          data: {
            businesses: communityMap.businesses,
            profile,
            // Counting the records we did load keeps every filter chip usable.
            categories: categoriesFailed
              ? countBusinessesByCategory(communityMap.businesses)
              : categoriesResult.value,
            transit: [],
            communityGeoJson: communityMap.communityGeoJson,
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
