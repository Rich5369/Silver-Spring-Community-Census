/**
 * Verifies that the frontend correctly consumes backend data.
 *
 * Run it against a live API, or offline to check the parts that do not need one:
 *
 *   npm run verify:data                       # uses http://127.0.0.1:8000
 *   API=http://localhost:8000 npm run verify:data
 *
 * The Census section runs a tract through the adapter using the *shape*
 * documented in backend/README.md. It exists so that the day Census ingestion
 * lands, one command says whether the frontend will render it. Nothing here is
 * imported by the app; no fixture value ever reaches the UI.
 */
import { registerHooks } from 'node:module';
import { existsSync, readFileSync } from 'node:fs';
import { fileURLToPath, pathToFileURL } from 'node:url';

const SRC = new URL('../src/', import.meta.url);
const API = process.env.API || 'http://127.0.0.1:8000';

// Stand in for the two things Vite does that plain Node does not.
globalThis.__VITE_ENV__ = { VITE_API_BASE_URL: '/' };
registerHooks({
  resolve(specifier, context, nextResolve) {
    if (specifier.startsWith('.') && !/\.(js|jsx|mjs|json)$/.test(specifier)) {
      const base = fileURLToPath(new URL(specifier, context.parentURL));
      for (const ext of ['.js', '.jsx']) {
        if (existsSync(base + ext)) {
          return { url: pathToFileURL(base + ext).href, shortCircuit: true };
        }
      }
    }
    return nextResolve(specifier, context);
  },
  load(url, context, nextLoad) {
    if (url.startsWith('file://') && url.includes('/src/') && url.endsWith('.js')) {
      const source = readFileSync(fileURLToPath(url), 'utf8');
      if (source.includes('import.meta.env')) {
        return {
          format: 'module',
          shortCircuit: true,
          source: source.replaceAll('import.meta.env', 'globalThis.__VITE_ENV__'),
        };
      }
    }
    return nextLoad(url, context);
  },
});

const { normalizeCommunityMap, normalizeBusinessCategories } =
  await import(new URL('services/api.js', SRC).href);
const { resolveCommunityProfile } = await import(new URL('services/useCommunityData.js', SRC).href);
const {
  queryBusinesses, describeResultCount, buildBusinessFilters,
  countBusinessesByCategory, findUncoveredCategories, OTHER_FILTER_ID,
} = await import(new URL('services/businessQuery.js', SRC).href);
const { mockBusinesses } = await import(new URL('data/mockBusinesses.js', SRC).href);
const { areAllDemoBusinesses } = await import(new URL('services/provenance.js', SRC).href);

let pass = 0;
let fail = 0;
const check = (name, got, want) => {
  const ok = JSON.stringify(got) === JSON.stringify(want);
  if (ok) pass += 1; else fail += 1;
  console.log(`${ok ? '  ok  ' : ' FAIL '} ${name}`);
  if (!ok) console.log(`        got  ${JSON.stringify(got)}\n        want ${JSON.stringify(want)}`);
};
const statValue = (profile, id) => profile.stats.find((stat) => stat.id === id)?.value;

console.log('\n# Offline: demo fallback (API unreachable or not configured)');
const fallback = resolveCommunityProfile(mockBusinesses, null);
check('mock records are recognised as demo', areAllDemoBusinesses(mockBusinesses), true);
check('profile is labelled demo', fallback.dataStatus, 'Demo profile — illustrative values only');
check('business count matches the mock layer', statValue(fallback, 'businesses'), String(mockBusinesses.length));
check('no live source is claimed', fallback.sources.some((s) => s.id === 'live-businesses'), false);
check('empty input does not throw', statValue(resolveCommunityProfile([], null), 'businesses'), '0');
check('malformed GeoJSON falls back', resolveCommunityProfile([], { type: 'Nonsense' }).dataStatus,
  'Demo profile — illustrative values only');

console.log('\n# Offline: Census readiness (contract shape from backend/README.md)');
// A bounding box around the Silver Spring study area, used only to prove the
// point-in-polygon lookup selects the tract that contains Fenton Village.
const ring = [[-77.05, 38.97], [-77.00, 38.97], [-77.00, 39.01], [-77.05, 39.01], [-77.05, 38.97]];
const evidence = (variable) => ({
  dataset: 'American Community Survey 5-Year Estimates (2024)',
  dataset_year: 2024,
  source_variable: variable,
  source_url: 'https://api.census.gov/data/2024/acs/acs5',
  organization: 'US Census Bureau',
});
const censusAreas = {
  type: 'FeatureCollection',
  features: [{
    type: 'Feature',
    id: '24031701701',
    properties: {
      geoid: '24031701701',
      name: 'Census Tract 7017.01; Montgomery County; Maryland',
      boundary_source: {
        dataset: 'TIGERweb Census Tracts (ACS 2024 vintage)',
        dataset_year: 2024,
        source_url: 'https://tigerweb.geo.census.gov/',
        organization: 'US Census Bureau',
      },
      metrics: {
        total_population: { value: 3503, unit: 'people', evidence: evidence('B01003_001E') },
        // A suppressed estimate. The backend contract says null means "not
        // available", never zero - the UI must say so rather than print 0.
        median_household_income: { value: null, unit: 'dollars', evidence: evidence('B19013_001E') },
      },
    },
    geometry: { type: 'Polygon', coordinates: [ring] },
  }],
};
const withCensus = resolveCommunityProfile(mockBusinesses, censusAreas);
check('default profile becomes the real tract', withCensus.areaName,
  'Census Tract 7017.01; Montgomery County; Maryland');
check('profile is no longer flagged demo', withCensus.dataStatus,
  'Connected Census data with source evidence');
check('ACS value is formatted', statValue(withCensus, 'total_population'), '3,503');
check('suppressed value reads as unavailable', statValue(withCensus, 'median_household_income'),
  'Data unavailable');
check('Census evidence is carried', withCensus.sources.some((s) => s.organization === 'US Census Bureau'), true);

console.log('\n# Offline: filter chips and category coverage');
const sample = [
  { name: 'A', category: 'Restaurant' }, { name: 'B', category: 'Restaurant' },
  { name: 'C', category: 'Retail' }, { name: 'D', category: 'Rocket Repair' },
];
const sampleFilters = buildBusinessFilters(sample);
check('all chip counts every record', sampleFilters.find((f) => f.id === 'all').count, 4);
check('group chip counts its categories', sampleFilters.find((f) => f.id === 'restaurants').count, 2);
check('unknown category surfaces an Other chip',
  sampleFilters.find((f) => f.id === OTHER_FILTER_ID)?.count, 1);
check('Other filter selects exactly the uncovered records',
  queryBusinesses({ businesses: sample, filter: OTHER_FILTER_ID }).map((b) => b.name), ['D']);
check('no Other chip when everything is covered',
  buildBusinessFilters(sample.slice(0, 3)).some((f) => f.id === OTHER_FILTER_ID), false);
check('backend-reported category alone can raise an Other chip',
  buildBusinessFilters(sample.slice(0, 3), [{ category: 'Rocket Repair', count: 9 }])
    .some((f) => f.id === OTHER_FILTER_ID), true);
check('category counts sort by size', countBusinessesByCategory(sample)[0],
  { category: 'Restaurant', count: 2 });
check('uncovered detection accepts plain strings',
  findUncoveredCategories(['Retail', 'Rocket Repair']), ['Rocket Repair']);
check('categories normalizer reads the documented shape',
  normalizeBusinessCategories({ count: 1, categories: [{ category: 'Cafe', count: 15 }] }),
  [{ category: 'Cafe', count: 15 }]);

console.log('\n# Offline: result-count wording');
check('filtered', describeResultCount(77, 207), 'Showing 77 of 207 businesses');
check('unfiltered', describeResultCount(207, 207), 'Showing all 207 businesses');
check('empty', describeResultCount(0, 207), 'No businesses match — 0 of 207');
check('nothing loaded', describeResultCount(0, 0), 'No business records loaded yet');

console.log(`\n# Live API at ${API}`);
let payload = null;
let liveCategories = null;
try {
  const response = await fetch(`${API}/api/v1/map/community`, { signal: AbortSignal.timeout(15000) });
  payload = await response.json();
  const categoriesResponse = await fetch(`${API}/api/v1/businesses/categories`,
    { signal: AbortSignal.timeout(15000) });
  liveCategories = normalizeBusinessCategories(await categoriesResponse.json());
} catch (error) {
  console.log(`  skip  API not reachable (${error.message}). Start it with:`);
  console.log('        cd backend && uvicorn app.main:app --port 8000');
}

if (payload) {
  const map = normalizeCommunityMap(payload);
  const businessCount = map.businesses.length;
  check('every business record normalizes', businessCount, payload.businesses.features.length);
  console.log(`  info  ${businessCount} businesses, ${map.communityGeoJson.features.length} areas`);

  if (liveCategories) {
    console.log(`  info  categories endpoint reports ${liveCategories.length} categories`);
    check('categories endpoint total matches the mapped layer',
      liveCategories.reduce((n, c) => n + c.count, 0), businessCount);
    check('no category the endpoint reports is unreachable',
      findUncoveredCategories(liveCategories).filter(
        (c) => !buildBusinessFilters(map.businesses, liveCategories).some((f) => f.id === OTHER_FILTER_ID),
      ), []);
  }

  const liveProfile = resolveCommunityProfile(map.businesses, map.communityGeoJson);
  check('panel business count matches the map', statValue(liveProfile, 'businesses'), String(businessCount));
  if (map.communityGeoJson.features.length === 0) {
    console.log('  info  No Census areas yet - profile stays on the labelled demo values.');
    check('demographics still labelled demo', liveProfile.dataStatus,
      'Demo profile — illustrative values only');
  } else {
    check('Census data is live', liveProfile.dataStatus, 'Connected Census data with source evidence');
  }

  const categories = [...new Set(map.businesses.map((b) => b.category))];
  const liveFilters = buildBusinessFilters(map.businesses, liveCategories ?? []);
  const reachable = new Set();
  liveFilters.filter((f) => f.id !== 'all').forEach((filter) => {
    queryBusinesses({ businesses: map.businesses, filter: filter.id })
      .forEach((b) => reachable.add(b.category));
  });
  check('every live category is reachable by a filter chip',
    categories.filter((c) => !reachable.has(c)), []);
  check('chip counts sum to the whole layer',
    liveFilters.filter((f) => f.id !== 'all').reduce((n, f) => n + f.count, 0), businessCount);
  check('all chip equals the layer size', liveFilters.find((f) => f.id === 'all').count, businessCount);

  const snapshotCategories = liveProfile.stats.filter((s) => s.id.startsWith('category-'));
  check('snapshot lists real categories', snapshotCategories.length > 0, true);
  check('snapshot category total equals the layer',
    liveProfile.stats.filter((s) => s.id.startsWith('category-'))
      .reduce((n, s) => n + Number(s.value), 0), businessCount);
  console.log(`  info  snapshot: ${snapshotCategories.map((s) => `${s.label}=${s.value}`).join(', ')}`);
}

console.log(`\n${pass} passed, ${fail} failed\n`);
process.exit(fail ? 1 : 0);
