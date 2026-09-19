import { useMemo, useState } from 'react';
import Header from './components/Header';
import InsightsPanel from './components/InsightsPanel';
import MapPanel from './components/MapPanel';
import QueryPanel from './components/QueryPanel';
import { buildBusinessFilters, queryBusinesses } from './services/businessQuery';
import { useCommunityData } from './services/useCommunityData';

function App() {
  const { data, status, issue, usingFallback } = useCommunityData();
  const [activeFilter, setActiveFilter] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedGeoJsonArea, setSelectedGeoJsonArea] = useState(null);
  const [fentonExploreKey, setFentonExploreKey] = useState(0);
  const selectedInsights = selectedGeoJsonArea ?? data.profile;
  // Once the default profile is a real tract, selecting that same tract would
  // otherwise compare it against itself.
  const comparisonAreas = useMemo(
    () => [data.profile, selectedGeoJsonArea].filter(
      (area, index, areas) => Boolean(area)
        && (index === 0 || area.areaId !== areas[0]?.areaId),
    ),
    [data.profile, selectedGeoJsonArea],
  );
  const visibleBusinesses = useMemo(
    () => queryBusinesses({ businesses: data.businesses, filter: activeFilter, searchTerm }),
    [activeFilter, data.businesses, searchTerm],
  );
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

  return (
    <div className="app-shell">
      <Header />
      <main className="workspace">
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
