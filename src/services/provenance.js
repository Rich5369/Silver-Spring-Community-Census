// One definition of "is this record demo data?", shared by the map notice, the
// business cards and the insights panel so they can never disagree about
// whether the user is looking at real data.
const DEMO_PATTERN = /demo|mock|illustrative/i;

export function isDemoBusiness(business, sources = []) {
  const sourceText = sources
    .map((source) => `${source?.organization ?? ''} ${source?.dataset ?? ''}`)
    .join(' ');

  return DEMO_PATTERN.test(`${business?.source ?? ''} ${sourceText}`);
}

// True only when every record is demo data. An empty list is not a demo layer:
// "no results" and "mock results" are different states for the user.
export function areAllDemoBusinesses(businesses = []) {
  return businesses.length > 0 && businesses.every((business) => isDemoBusiness(business));
}

export function isDemoStatus(status) {
  return DEMO_PATTERN.test(status || '');
}
