import { describeResultCount } from '../services/businessQuery';

function QueryPanel({
  activeFilter,
  filters = [],
  searchTerm,
  resultCount,
  totalCount = 0,
  onFilterChange,
  onSearchChange,
  onClear,
  dataStatus,
  dataIssue,
  usingFallback,
}) {
  return (
    <section className="query-panel" aria-label="Search and filters">
      <div className="search-area">
        <label htmlFor="community-query">Search businesses</label>
        <form className="search-field" onSubmit={(event) => event.preventDefault()}>
          <span aria-hidden="true">⌕</span>
          <input
            id="community-query"
            type="search"
            value={searchTerm}
            onChange={(event) => onSearchChange(event.target.value)}
            placeholder="Search businesses by name or category..."
            aria-describedby="business-search-help"
          />
        </form>
        <span className="visually-hidden" id="business-search-help">
          Results update as you type.
        </span>
      </div>

      <div className="filter-area" role="group" aria-labelledby="business-filter-label">
        <div className="filter-summary">
          <span className="filter-label" id="business-filter-label">Filter businesses</span>
          <output className="result-count" aria-live="polite">
            {describeResultCount(resultCount, totalCount)}
          </output>
        </div>
        <div className="filter-list" aria-label="Business categories">
          {filters.map((filter) => {
            const isActive = activeFilter === filter.id;
            const hasCount = Number.isFinite(filter.count);
            // A chip that cannot return anything is disabled rather than hidden,
            // so the set of categories on screen stays stable while searching.
            const isEmpty = hasCount && filter.count === 0;

            return (
              <button
                className={isActive ? 'filter-chip active' : 'filter-chip'}
                type="button"
                key={filter.id}
                aria-pressed={isActive}
                disabled={isEmpty && !isActive}
                aria-label={hasCount
                  ? `${filter.label}, ${filter.count} ${filter.count === 1 ? 'business' : 'businesses'}`
                  : filter.label}
                onClick={() => onFilterChange(filter.id)}
              >
                {isActive && <span className="active-check" aria-hidden="true">✓</span>}
                {filter.label}
                {hasCount && <span className="filter-chip-count" aria-hidden="true">{filter.count}</span>}
              </button>
            );
          })}
          <button
            className="filter-chip clear-filter"
            type="button"
            onClick={onClear}
            disabled={activeFilter === 'all' && searchTerm.length === 0}
          >
            Clear Filters
          </button>
        </div>
        <p className="data-load-status" role="status">
          {dataStatus === 'loading' && 'Loading community data…'}
          {dataStatus === 'error' && dataIssue === 'malformed'
            && 'Some API data was invalid — showing safe demo data.'}
          {dataStatus === 'error' && dataIssue !== 'malformed'
            && 'API unavailable — showing safe demo data.'}
          {dataStatus === 'partial' && dataIssue === 'malformed'
            && 'Some API data was invalid — available sections remain active.'}
          {dataStatus === 'partial' && dataIssue !== 'malformed'
            && 'Some data is unavailable — available sections remain active.'}
          {dataStatus === 'success' && usingFallback && 'Demo data mode — no backend URL configured.'}
          {dataStatus === 'success' && !usingFallback && 'Connected to stored Census and business data.'}
          {dataStatus === 'error' && 'The API could not be reached. Start the backend or configure VITE_API_BASE_URL.'}
        </p>
      </div>
    </section>
  );
}

export default QueryPanel;
