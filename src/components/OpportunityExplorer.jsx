function formatCount(value) {
  return value == null ? 'Not available' : new Intl.NumberFormat('en-US').format(value);
}

function OpportunityExplorer({ insights, businesses = [] }) {
  const categories = [...new Set(businesses.map((business) => business.category).filter(Boolean))].sort();
  const selectedCategory = categories.find((category) => /cafe|coffee/i.test(category)) || categories[0];
  const competition = selectedCategory
    ? businesses.filter((business) => business.category === selectedCategory).length
    : null;
  const metrics = insights?.opportunityMetrics ?? {};
  const hasCensusMetrics = Object.keys(metrics).length > 0;
  const evidence = insights?.sources?.filter((source) => /census|acs/i.test(`${source.organization} ${source.dataset}`)) ?? [];

  return (
    <section className="opportunity-explorer" aria-labelledby="opportunity-title">
      <p className="eyebrow">Evidence-based exploration</p>
      <h3 id="opportunity-title">Business Opportunity Explorer</h3>
      <p className="opportunity-intro">
        Compare local context and existing competition. These indicators describe
        the area; they are not a prediction of business success.
      </p>
      <div className="opportunity-controls">
        <label htmlFor="opportunity-category">Considering opening</label>
        <select id="opportunity-category" value={selectedCategory || ''} disabled={!selectedCategory} readOnly>
          {selectedCategory && <option>{selectedCategory}</option>}
          {!selectedCategory && <option>No business categories available</option>}
        </select>
      </div>
      <dl className="opportunity-facts">
        <div><dt>Existing {selectedCategory || 'business'} records</dt><dd>{formatCount(competition)}</dd></div>
        <div><dt>Businesses mapped nearby</dt><dd>{formatCount(businesses.length)}</dd></div>
        {hasCensusMetrics && Object.entries(metrics).map(([key, metric]) => (
          <div key={key}><dt>{metric.label}</dt><dd>{metric.value == null ? 'Not available' : `${metric.value}${metric.unit === 'percent' ? '%' : ''}`}</dd></div>
        ))}
      </dl>
      <p className="opportunity-evidence">
        {hasCensusMetrics && evidence.length > 0
          ? `Census evidence: ${evidence[0].dataset} (${evidence[0].year}).`
          : 'Census opportunity indicators are not available in the current demo dataset.'}
      </p>
    </section>
  );
}

export default OpportunityExplorer;
