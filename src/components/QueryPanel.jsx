import { filters } from '../data/placeholderData';

function QueryPanel() {
  return (
    <section className="query-panel" aria-label="Search and filters">
      <div className="search-area">
        <label htmlFor="community-query">Explore the community</label>
        <div className="search-field">
          <span aria-hidden="true">⌕</span>
          <input
            id="community-query"
            type="search"
            placeholder="Try “restaurants in Fenton Village”"
          />
          <button type="button">Search</button>
        </div>
      </div>

      <div className="filter-area">
        <span className="filter-label">Filters</span>
        <div className="filter-list">
          {filters.map((filter, index) => (
            <button
              className={index === 0 ? 'filter-chip active' : 'filter-chip'}
              type="button"
              key={filter}
            >
              {filter}
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}

export default QueryPanel;
