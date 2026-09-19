import { useMemo, useState } from 'react';
import Header from './components/Header';
import InsightsPanel from './components/InsightsPanel';
import MapPanel from './components/MapPanel';
import QueryPanel from './components/QueryPanel';
import { mockBusinesses } from './data/mockBusinesses';
import { queryBusinesses } from './services/businessQuery';

function App() {
  const [activeFilter, setActiveFilter] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const visibleBusinesses = useMemo(
    () => queryBusinesses({ businesses: mockBusinesses, filter: activeFilter, searchTerm }),
    [activeFilter, searchTerm],
  );

  const clearFilters = () => {
    setActiveFilter('all');
    setSearchTerm('');
  };

  return (
    <div className="app-shell">
      <Header />
      <main className="workspace">
        <QueryPanel
          activeFilter={activeFilter}
          searchTerm={searchTerm}
          resultCount={visibleBusinesses.length}
          onFilterChange={setActiveFilter}
          onSearchChange={setSearchTerm}
          onClear={clearFilters}
        />
        <div className="content-grid">
          <MapPanel
            businesses={visibleBusinesses}
            hasActiveQuery={activeFilter !== 'all' || searchTerm.trim().length > 0}
          />
          <InsightsPanel />
        </div>
      </main>
    </div>
  );
}

export default App;
