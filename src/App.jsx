import { Suspense, lazy, useEffect, useMemo, useRef, useState } from 'react';
import Header from './components/Header';
import AskCommunity from './components/AskCommunity';
import HomeIntro from './components/HomeIntro';
import { answerAreaQuestion } from './services/areaQuestion';
import QueryPanel from './components/QueryPanel';
import { buildBusinessFilters, queryBusinesses } from './services/businessQuery';
import { useCommunityData } from './services/useCommunityData';
import { useDebouncedValue } from './utils/useDebouncedValue';
import { askCommunityQuestion, getGovernmentServiceRequests, getGovernmentSummary, getGovernmentTrends } from './services/api';

// The hero is the first thing on the page and needs none of these, so they are
// split out of the initial bundle. MapPanel carries Leaflet and react-leaflet
// with it, which is the largest dependency in the app by a wide margin.
const PlanningTrends = lazy(() => import('./components/PlanningTrends'));
const MapPanel = lazy(() => import('./components/MapPanel'));
const OpportunityExplorer = lazy(() => import('./components/OpportunityExplorer'));
const GovernmentPlanningPanel = lazy(() => import('./components/GovernmentPlanningPanel'));

// Fetch the split chunks once the page is idle, so a section is almost always
// in memory before the reader scrolls or clicks to it. Without this, the first
// click on "View community trends" would pay for the download.
const preloadSections = () => {
  import('./components/PlanningTrends');
  import('./components/MapPanel');
  import('./components/OpportunityExplorer');
  import('./components/GovernmentPlanningPanel');
};

// One shared empty array, so "nothing selected" keeps a stable identity.
const EMPTY_LIST = [];

function App() {
  const { data, status, issue, usingFallback } = useCommunityData();
  const [activeFilter, setActiveFilter] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedGeoJsonArea, setSelectedGeoJsonArea] = useState(null);
  const [fentonExploreKey, setFentonExploreKey] = useState(0);
  const [question, setQuestion] = useState('');
  const [queryState, setQueryState] = useState({ status: 'idle', result: null, error: null });
  const [governmentSummary, setGovernmentSummary] = useState(null);
  const [governmentTrends, setGovernmentTrends] = useState(null);
  const [serviceRequests, setServiceRequests] = useState(null);
  // <details> renders its children even while closed, so the explorer is only
  // mounted once it is actually opened - otherwise lazy-loading it would save
  // nothing.
  const [areToolsOpen, setAreToolsOpen] = useState(false);
  // These feed the map. Rebuilding them inline handed Leaflet a new array on
  // every render, which re-ran the layer effects that depend on them even when
  // nothing about the query had changed.
  const queryFacilities = useMemo(
    () => (queryState.result?.parsed?.intent === 'facilities'
      ? (queryState.result.facilities ?? EMPTY_LIST) : EMPTY_LIST),
    [queryState.result],
  );
  const highlightedAreaIds = useMemo(
    () => queryState.result?.map?.area_geoids ?? EMPTY_LIST,
    [queryState.result],
  );
  const selectedInsights = selectedGeoJsonArea ?? data.profile;
  const requestVersion = useRef(0);
  const businessToolsRef = useRef(null);
  const selectArea = (area) => {
    requestVersion.current += 1;
    setSelectedGeoJsonArea(area);
    setQueryState({ status: 'idle', result: null, error: null });
    setQuestion('');
  };
  useEffect(() => {
    let active = true;
    getGovernmentSummary()
      .then((summary) => { if (active) setGovernmentSummary(summary); })
      .catch(() => { if (active) setGovernmentSummary(null); });
    getGovernmentTrends()
      .then((trends) => { if (active) setGovernmentTrends(trends); })
      .catch(() => { if (active) setGovernmentTrends(null); });
    getGovernmentServiceRequests()
      .then((requests) => { if (active) setServiceRequests(requests); })
      .catch(() => { if (active) setServiceRequests(null); });
    return () => { active = false; };
  }, []);
  useEffect(() => {
    const idle = window.requestIdleCallback ?? ((callback) => setTimeout(callback, 200));
    const cancel = window.cancelIdleCallback ?? clearTimeout;
    const handle = idle(preloadSections);
    return () => cancel(handle);
  }, []);
  // The input stays on `searchTerm` so typing is immediate; the filtering below
  // runs on the settled term. Clearing is an explicit action rather than
  // typing, so it takes effect at once instead of trailing the debounce.
  const debouncedSearchTerm = useDebouncedValue(searchTerm, 200);
  const settledSearchTerm = searchTerm === '' ? '' : debouncedSearchTerm;
  // Rebuilt on every render before this was memoised, which made every memo
  // downstream of it recompute on every render as well.
  const queryBusinessIds = useMemo(
    () => (queryState.result?.parsed?.intent === 'nearby_businesses'
      ? new Set((queryState.result.businesses ?? []).map((business) => business.id))
      : null),
    [queryState.result],
  );
  const visibleBusinesses = useMemo(() => {
    const filtered = queryBusinesses({ businesses: data.businesses, filter: activeFilter, searchTerm: settledSearchTerm });
    return queryBusinessIds ? filtered.filter((business) => queryBusinessIds.has(business.id)) : filtered;
  }, [activeFilter, data.businesses, queryBusinessIds, settledSearchTerm]);
  // Chip counts describe what the current search would return, so a chip never
  // promises results it cannot deliver. Categories the backend reports but the
  // curated groups do not cover surface as an "Other" chip.
  const searchMatches = useMemo(
    () => queryBusinesses({ businesses: data.businesses, searchTerm: settledSearchTerm }),
    [data.businesses, settledSearchTerm],
  );
  const filters = useMemo(
    () => buildBusinessFilters(searchMatches, data.categories),
    [searchMatches, data.categories],
  );

  const clearFilters = () => {
    setActiveFilter('all');
    setSearchTerm('');
  };

  const exploreFentonVillage = () => {
    clearFilters();
    selectArea(null);
    setFentonExploreKey((key) => key + 1);
  };

  const scrollToSection = (id) => {
    const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    document.getElementById(id)?.scrollIntoView({
      behavior: reduceMotion ? 'auto' : 'smooth',
      block: 'start',
    });
  };

  const openBusinessExplorer = () => {
    if (businessToolsRef.current) businessToolsRef.current.open = true;
    scrollToSection('business-explorer');
  };

  const askQuestion = async () => {
    const submitted = question.trim();
    if (!submitted) return;
    const version = ++requestVersion.current;
    setQueryState({ status: 'loading', result: null, error: null });
    try {
      const result = selectedGeoJsonArea
        ? answerAreaQuestion(submitted, selectedGeoJsonArea)
        : await askCommunityQuestion(submitted);
      if (version !== requestVersion.current) return;
      setQueryState({ status: 'success', result, error: null });
      setActiveFilter('all');
      setSearchTerm('');
      if (!selectedGeoJsonArea) setFentonExploreKey((key) => key + 1);
    } catch (error) {
      if (version !== requestVersion.current) return;
      setQueryState({ status: 'error', result: null, error });
    }
  };

  return (
    <div className="app-shell">
      <Header />
      <main>
        <HomeIntro
          onExplore={() => scrollToSection('community-explorer')}
          onViewTrends={() => scrollToSection('planning-trends')}
        />
        <div className="workspace">
          {/* The fallback carries the section's id and shape so "View community
              trends" scrolls correctly even before the chunk has arrived. */}
          <Suspense fallback={(
            <section className="planning-trends section-loading" id="planning-trends" aria-busy="true">
              <p>Loading community trends…</p>
            </section>
          )}>
            <PlanningTrends
              insights={selectedInsights}
              trends={governmentTrends}
              trendGeography={governmentSummary?.study_area?.study_area?.name}
              onExploreMap={() => scrollToSection('community-explorer')}
            />
          </Suspense>
          <div className="explorer-stage" id="community-explorer">
            <div className="current-area" aria-live="polite">
              <span>Currently exploring</span>
              <strong>{selectedInsights.areaName}</strong>
              {selectedGeoJsonArea && <small>Montgomery County, Maryland</small>}
            </div>
            <QueryPanel
              activeFilter={activeFilter}
              filters={filters}
              searchTerm={searchTerm}
              resultCount={visibleBusinesses.length}
              totalCount={data.businesses.length}
              onFilterChange={setActiveFilter}
              onSearchChange={setSearchTerm}
              onClear={clearFilters}
              dataStatus={status}
              dataIssue={issue}
              usingFallback={usingFallback}
            />
            <div className="content-grid">
              <Suspense fallback={<div className="map-panel section-loading" aria-busy="true"><p>Loading map…</p></div>}>
                <MapPanel
                  areaName={selectedInsights.areaName}
                  businesses={queryState.result?.parsed?.intent === 'facilities' ? EMPTY_LIST : visibleBusinesses}
                  facilities={queryFacilities}
                  totalBusinessCount={data.businesses.length}
                  businessLayerAvailable={data.businesses.length > 0}
                  evidenceSources={data.profile.sources}
                  communityGeoJson={data.communityGeoJson}
                  selectedAreaId={selectedGeoJsonArea?.areaId ?? null}
                  highlightedAreaIds={highlightedAreaIds}
                  onAreaSelect={selectArea}
                  onDefaultAreaSelect={() => selectArea(null)}
                  onExploreFenton={exploreFentonVillage}
                  exploreKey={fentonExploreKey}
                  hasActiveQuery={activeFilter !== 'all' || searchTerm.trim().length > 0 || queryFacilities.length > 0}
                  isBusinessLoading={status === 'loading'}
                />
              </Suspense>
              <AskCommunity
                question={question}
                onQuestionChange={setQuestion}
                onAsk={askQuestion}
                status={queryState.status}
                result={queryState.result}
                error={queryState.error}
                areaName={selectedGeoJsonArea?.areaName ?? 'Fenton Village, Silver Spring, Maryland'}
                isAreaSelected={Boolean(selectedGeoJsonArea)}
              />
            </div>
          </div>
          <div className="business-explorer-callout">
            <p><strong>Exploring a business opportunity?</strong><span>Compare mapped competition with available community context.</span></p>
            <button className="secondary-button" type="button" onClick={openBusinessExplorer}>Open Business Opportunity Explorer</button>
          </div>
          <details
            className="exploration-tools"
            id="business-explorer"
            ref={businessToolsRef}
            onToggle={(event) => setAreToolsOpen(event.currentTarget.open)}
          >
            <summary>Business Opportunity Explorer and planning context</summary>
            {areToolsOpen && (
              <Suspense fallback={<p className="section-loading">Loading explorer…</p>}>
                <OpportunityExplorer insights={data.profile} businesses={data.businesses} />
                <GovernmentPlanningPanel summary={governmentSummary} trends={governmentTrends} serviceRequests={serviceRequests} />
              </Suspense>
            )}
          </details>
        </div>
      </main>
    </div>
  );
}

export default App;
