import BusinessStatus from './BusinessStatus';

export default function BusinessList({
  businesses,
  evidenceSources,
  selectedBusinessId = null,
  onViewOnMap,
  emptyMessage,
}) {
  return (
    <div className="business-list-view">
      <p className="list-intro">
        Every business below matches the current search and filters, in the same order as the map.
      </p>
      {businesses.length === 0 ? (
        <p className="list-empty" role="status">No businesses found. {emptyMessage}</p>
      ) : (
        <ul className="business-results" aria-label={`Business results, ${businesses.length} matching`}>
          {businesses.map((business) => {
            const isSelected = business.id === selectedBusinessId;

            return (
              <li key={business.id}>
                <article
                  className={isSelected ? 'business-card selected' : 'business-card'}
                  aria-current={isSelected ? 'true' : undefined}
                >
                  <h3>
                    {business.name}
                    {isSelected && <span className="selected-flag">Selected</span>}
                  </h3>
                  <dl>
                    <div>
                      <dt>Category</dt>
                      <dd>{business.category}</dd>
                    </div>
                    <div>
                      <dt>Address</dt>
                      <dd>{business.address || 'Address not provided'}</dd>
                    </div>
                    <div>
                      <dt>Data source</dt>
                      <dd>
                        <BusinessStatus
                          business={business}
                          sources={evidenceSources.filter((source) => business.sourceIds?.includes(source.id))}
                        />
                      </dd>
                    </div>
                  </dl>
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() => onViewOnMap(business)}
                    aria-label={`View ${business.name} on map`}
                  >
                    View on map
                  </button>
                </article>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
