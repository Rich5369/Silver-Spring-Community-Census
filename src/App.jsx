import { useEffect, useMemo, useState } from 'react';
import Header from './components/Header';
import AskCommunity from './components/AskCommunity';
import InsightsPanel from './components/InsightsPanel';
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
  // Once the default profile is a real tract, selecting that same tract would
  // otherwise compare it against itself.
  const comparisonAreas = useMemo(
    () => [data.profile, selectedGeoJsonArea].filter(
      (area, index, areas) => Boolean(area)
        && (index === 0 || area.areaId !== areas[0]?.areaId),
    ),
    [data.profile, selectedGeoJsonArea],
  );
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
    setSelectedGeoJsonArea(null);
    setFentonExploreKey((key) => key + 1);
  };

  const askQuestion = async () => {
    const submitted = question.trim();
    if (!submitted) return;
    setQueryState({ status: 'loading', result: null, error: null });
    try {
      const result = await askCommunityQuestion(submitted);
      setQueryState({ status: 'success', result, error: null });
      setActiveFilter('all');
      setSearchTerm('');
      setFentonExploreKey((key) => key + 1);
    } catch (error) {
      setQueryState({ status: 'error', result: null, error });
    }
  };

  return (
    <div className="app-shell">
      <Header />
      <main className="workspace">
        <div className="main-layout">
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
            onAreaSelect={setSelectedGeoJsonArea}
            onDefaultAreaSelect={() => setSelectedGeoJsonArea(null)}
            onExploreFenton={exploreFentonVillage}
            exploreKey={fentonExploreKey}
            hasActiveQuery={activeFilter !== 'all' || searchTerm.trim().length > 0}
          />
          </div>
          <aside className="right-rail" aria-label="Community data and planning tools">
            <AskCommunity
              question={question}
              onQuestionChange={setQuestion}
              onAsk={askQuestion}
              status={queryState.status}
              result={queryState.result}
              error={queryState.error}
            />
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
            <InsightsPanel
              insights={selectedInsights}
              comparisonAreas={comparisonAreas}
              businesses={data.businesses}
              governmentSummary={governmentSummary}
              governmentTrends={governmentTrends}
              isAreaSelected={Boolean(selectedGeoJsonArea)}
              hasQueryResult={Boolean(queryState.result)}
            />
          </aside>
        </div>
      </main>
    </div>
  );
}

export default App;
