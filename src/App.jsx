import { useEffect, useMemo, useRef, useState } from 'react';
import Header from './components/Header';
import AskCommunity from './components/AskCommunity';
import OpportunityExplorer from './components/OpportunityExplorer';
import GovernmentPlanningPanel from './components/GovernmentPlanningPanel';
import PlanningTrends from './components/PlanningTrends';
import HomeIntro from './components/HomeIntro';
import { answerAreaQuestion } from './services/areaQuestion';
import MapPanel from './components/MapPanel';
import QueryPanel from './components/QueryPanel';
import { buildBusinessFilters, queryBusinesses } from './services/businessQuery';
import { useCommunityData } from './services/useCommunityData';
import { askCommunityQuestion, getGovernmentSummary, getGovernmentTrends } from './services/api';

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
  const selectedInsights = selectedGeoJsonArea ?? data.profile;
  const requestVersion = useRef(0);
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
    return () => { active = false; };
  }, []);
  const queryBusinessIds = queryState.result?.parsed?.intent === 'nearby_businesses'
    ? new Set((queryState.result.businesses ?? []).map((business) => business.id))
    : null;
  const visibleBusinesses = useMemo(() => {
    const filtered = queryBusinesses({ businesses: data.businesses, filter: activeFilter, searchTerm });
    return queryBusinessIds ? filtered.filter((business) => queryBusinessIds.has(business.id)) : filtered;
  }, [activeFilter, data.businesses, queryBusinessIds, searchTerm]);
  // Chip counts describe what the current search would return, so a chip never
  // promises results it cannot deliver. Categories the backend reports but the
  // curated groups do not cover surface as an "Other" chip.
  const searchMatches = useMemo(
    () => queryBusinesses({ businesses: data.businesses, searchTerm }),
    [data.businesses, searchTerm],
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

  const scrollToExplorer = () => {
    const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    document.getElementById('community-explorer')?.scrollIntoView({
      behavior: reduceMotion ? 'auto' : 'smooth',
      block: 'start',
    });
  };

  const exploreFentonFromHome = () => {
    exploreFentonVillage();
    scrollToExplorer();
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
        <HomeIntro onExplore={scrollToExplorer} onExploreFenton={exploreFentonFromHome} />
        <div className="workspace" id="community-explorer">
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
            <MapPanel
            areaName={selectedInsights.areaName}
            businesses={visibleBusinesses}
            totalBusinessCount={data.businesses.length}
            businessLayerAvailable={data.businesses.length > 0}
            evidenceSources={data.profile.sources}
            communityGeoJson={data.communityGeoJson}
            selectedAreaId={selectedGeoJsonArea?.areaId ?? null}
            highlightedAreaIds={queryState.result?.map?.area_geoids ?? []}
            onAreaSelect={selectArea}
            onDefaultAreaSelect={() => selectArea(null)}
            onExploreFenton={exploreFentonVillage}
            exploreKey={fentonExploreKey}
            hasActiveQuery={activeFilter !== 'all' || searchTerm.trim().length > 0}
            isBusinessLoading={status === 'loading'}
            />
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
          <PlanningTrends
            insights={selectedInsights}
            trends={governmentTrends}
            trendGeography={governmentSummary?.study_area?.study_area?.name}
          />
          <details className="exploration-tools">
            <summary>Business Opportunity Explorer and planning context</summary>
            <OpportunityExplorer insights={data.profile} businesses={data.businesses} />
            <GovernmentPlanningPanel summary={governmentSummary} trends={governmentTrends} />
          </details>
        </div>
      </main>
    </div>
  );
}

export default App;
