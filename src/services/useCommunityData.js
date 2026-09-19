import { useEffect, useState } from 'react';
import { fentonVillageInsights } from '../data/communityInsights';
import { mockBusinesses } from '../data/mockBusinesses';
import {
  getBusinesses,
  getCommunityProfile,
  getSources,
  getTransit,
  isApiConfigured,
} from './api';

const fallbackData = {
  businesses: mockBusinesses,
  profile: fentonVillageInsights,
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

    Promise.allSettled([
      getBusinesses(options),
      getCommunityProfile(area, options),
      getSources(area, options),
      getTransit(options),
    ])
      .then((results) => {
        if (controller.signal.aborted) return;
        const [businessesResult, profileResult, sourcesResult, transitResult] = results;
        const failures = results.filter((result) => result.status === 'rejected');
        const businesses = businessesResult.status === 'fulfilled'
          ? businessesResult.value
          : fallbackData.businesses;
        const profile = profileResult.status === 'fulfilled'
          ? profileResult.value
          : fallbackData.profile;
        const sources = profileResult.status === 'rejected'
          ? fallbackData.profile.sources
          : sourcesResult.status === 'fulfilled' ? sourcesResult.value : [];
        const transit = transitResult.status === 'fulfilled' ? transitResult.value : [];
        const error = failures[0]?.reason ?? null;
        const issue = failures.some((result) => (
          result.reason?.code === 'MALFORMED_RESPONSE' || result.reason instanceof SyntaxError
        )) ? 'malformed' : failures.length > 0 ? 'api' : null;

        if (import.meta.env.DEV && failures.length > 0) {
          console.error('Some community data could not be loaded; safe fallbacks are active.', error);
        }

        setState({
          status: failures.length === 0
            ? 'success'
            : failures.length === results.length ? 'error' : 'partial',
          data: {
            businesses,
            profile: { ...profile, sources },
            transit,
            communityGeoJson: null,
          },
          error,
          issue,
          usingFallback: failures.length > 0,
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
