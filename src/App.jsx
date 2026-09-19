import { useMemo, useState } from 'react';
import Header from './components/Header';
import InsightsPanel from './components/InsightsPanel';
import MapPanel from './components/MapPanel';
import QueryPanel from './components/QueryPanel';
import { queryBusinesses } from './services/businessQuery';
import { useCommunityData } from './services/useCommunityData';

function App() {
  const { data, status, issue, usingFallback } = useCommunityData();
  const [activeFilter, setActiveFilter] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedGeoJsonArea, setSelectedGeoJsonArea] = useState(null);
  const [fentonExploreKey, setFentonExploreKey] = useState(0);
  const selectedInsights = selectedGeoJsonArea ?? data.profile;
  const comparisonAreas = useMemo(
    () => [data.profile, selectedGeoJsonArea].filter(Boolean),
    [data.profile, selectedGeoJsonArea],
  );
  const visibleBusinesses = useMemo(
    () => queryBusinesses({ businesses: data.businesses, filter: activeFilter, searchTerm }),
    [activeFilter, data.businesses, searchTerm],
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

  return (
    <div className="app-shell">
      <Header />
      <main className="workspace">
        <QueryPanel
          activeFilter={activeFilter}
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
            onAreaSelect={setSelectedGeoJsonArea}
            onDefaultAreaSelect={() => setSelectedGeoJsonArea(null)}
            onExploreFenton={exploreFentonVillage}
            exploreKey={fentonExploreKey}
            hasActiveQuery={activeFilter !== 'all' || searchTerm.trim().length > 0}
          />
          <InsightsPanel
            insights={selectedInsights}
            comparisonAreas={comparisonAreas}
            businesses={data.businesses}
          />
        </div>
      </main>
    </div>
  );
}

export default App;
