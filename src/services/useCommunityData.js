import { useEffect, useState } from 'react';
import { fentonVillageInsights } from '../data/communityInsights';
import { mockBusinesses } from '../data/mockBusinesses';
import {
  getCommunityMap,
  isApiConfigured,
} from './api';

const fallbackData = {
  businesses: mockBusinesses,
  profile: fentonVillageInsights,
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

    getCommunityMap(options)
      .then((communityMap) => {
        if (controller.signal.aborted) return;
        setState({
          status: 'success',
          data: {
            businesses: communityMap.businesses,
            profile: fallbackData.profile,
            transit: [],
            communityGeoJson: communityMap.communityGeoJson,
          },
          error: null,
          issue: null,
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
