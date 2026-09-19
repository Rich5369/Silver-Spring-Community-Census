import { mockBusinesses } from './mockBusinesses';

const countBusinessesByCategory = (category) => (
  mockBusinesses.filter((business) => business.category === category).length
);

export const fentonVillageInsights = {
  areaName: 'Fenton Village',
  dataStatus: 'Demo profile — illustrative values only',
  summary: 'A walkable commercial district represented here with mock community indicators.',
  stats: [
    {
      id: 'population',
      label: 'Population',
      value: 'Demo: 8,200',
      note: 'Illustrative estimate',
    },
    {
      id: 'income',
      label: 'Median household income',
      value: 'Demo: $84K',
      note: 'Illustrative estimate',
    },
    {
      id: 'language',
      label: 'Multilingual households',
      value: 'Demo: 38%',
      note: 'Illustrative estimate',
    },
    {
      id: 'businesses',
      label: 'Businesses shown',
      value: String(mockBusinesses.length),
      note: 'Mock map records',
    },
    {
      id: 'restaurants',
      label: 'Restaurants',
      value: String(countBusinessesByCategory('Restaurant')),
      note: 'Mock map records',
    },
    {
      id: 'retail',
      label: 'Retail',
      value: String(countBusinessesByCategory('Retail')),
      note: 'Mock map records',
    },
  ],
  sources: [
    {
      organization: 'Demo project data',
      dataset: 'Fenton Village mock profile',
      year: 'Not applicable',
      geography: 'Illustrative Fenton Village area',
      table: 'No verified table connected',
      url: '',
    },
  ],
};
