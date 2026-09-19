import { businessFilters } from '../services/businessQuery';

function QueryPanel({
  activeFilter,
  searchTerm,
  resultCount,
  onFilterChange,
  onSearchChange,
  onClear,
  dataStatus,
  usingFallback,
}) {
  return (
    <section className="query-panel" aria-label="Search and filters">
      <div className="search-area">
        <label htmlFor="community-query">Search the map</label>
        <form className="search-field" onSubmit={(event) => event.preventDefault()}>
          <span aria-hidden="true">⌕</span>
          <input
            id="community-query"
            type="search"
            value={searchTerm}
            onChange={(event) => onSearchChange(event.target.value)}
            placeholder="Search businesses or explore the community..."
          />
          <button type="submit">Search</button>
        </form>
      </div>

      <div className="filter-area">
        <div className="filter-summary">
          <span className="filter-label">Filter businesses</span>
          <output className="result-count" aria-live="polite">
            {resultCount} {resultCount === 1 ? 'result' : 'results'}
          </output>
        </div>
        <div className="filter-list">
          {businessFilters.map((filter) => {
            const isActive = activeFilter === filter.id;

            return (
              <button
                className={isActive ? 'filter-chip active' : 'filter-chip'}
                type="button"
                key={filter.id}
                aria-pressed={isActive}
                onClick={() => onFilterChange(filter.id)}
              >
                {isActive && <span className="active-check" aria-hidden="true">✓</span>}
                {filter.label}
              </button>
            );
          })}
          <button className="filter-chip clear-filter" type="button" onClick={onClear}>
            Clear Filters
          </button>
        </div>
        <p className="data-load-status" role="status">
          {dataStatus === 'loading' && 'Loading community data…'}
          {dataStatus === 'error' && 'API unavailable — showing safe demo data.'}
          {dataStatus === 'success' && usingFallback && 'Demo data mode — no backend URL configured.'}
        </p>
      </div>
    </section>
  );
}

export default QueryPanel;
