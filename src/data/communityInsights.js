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
      sourceIds: ['demo-community-profile'],
    },
    {
      id: 'income',
      label: 'Median household income',
      value: 'Demo: $84K',
      note: 'Illustrative estimate',
      sourceIds: ['demo-community-profile'],
    },
    {
      id: 'language',
      label: 'Multilingual households',
      value: 'Demo: 38%',
      note: 'Illustrative estimate',
      sourceIds: ['demo-community-profile'],
    },
    {
      id: 'businesses',
      label: 'Businesses shown',
      value: String(mockBusinesses.length),
      note: 'Mock map records',
      sourceIds: ['demo-businesses'],
    },
    {
      id: 'restaurants',
      label: 'Restaurants',
      value: String(countBusinessesByCategory('Restaurant')),
      note: 'Mock map records',
      sourceIds: ['demo-businesses'],
    },
    {
      id: 'retail',
      label: 'Retail',
      value: String(countBusinessesByCategory('Retail')),
      note: 'Mock map records',
      sourceIds: ['demo-businesses'],
    },
  ],
  sources: [
    {
      id: 'demo-community-profile',
      organization: 'Demo project data',
      dataset: 'Fenton Village mock profile',
      year: 'Not applicable',
      geography: 'Illustrative Fenton Village area',
      table: 'No verified table connected',
      url: '',
    },
    {
      id: 'demo-businesses',
      organization: 'Silver Spring Community Census demo',
      dataset: 'Fenton Village mock business layer',
      year: 'Demo data',
      geography: 'Illustrative Fenton Village area',
      table: 'Mock business records',
      url: '',
    },
  ],
};
