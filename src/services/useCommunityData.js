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
};

export function useCommunityData(area) {
  const [state, setState] = useState({
    status: isApiConfigured ? 'loading' : 'success',
    data: fallbackData,
    error: null,
    usingFallback: !isApiConfigured,
  });

  useEffect(() => {
    if (!isApiConfigured) return undefined;

    const controller = new AbortController();
    const options = { signal: controller.signal };
    setState((current) => ({ ...current, status: 'loading', error: null }));

    Promise.all([
      getBusinesses(options),
      getCommunityProfile(area, options),
      getSources(area, options),
      getTransit(options),
    ])
      .then(([businesses, profile, sources, transit]) => {
        setState({
          status: 'success',
          data: { businesses, profile: { ...profile, sources }, transit },
          error: null,
          usingFallback: false,
        });
      })
      .catch((error) => {
        if (error.name === 'AbortError') return;
        setState({
          status: 'error',
          data: fallbackData,
          error,
          usingFallback: true,
        });
      });

    return () => controller.abort();
  }, [area]);

  return state;
}
