function GovernmentPlanningPanel({ summary }) {
  if (!summary) return null;

  const studyArea = summary.study_area ?? {};
  const metrics = (studyArea.community_snapshot ?? [])
    .filter((item) => item.available && item.value !== null && item.unit === 'percent')
    .slice(0, 4);
  const categories = studyArea.business_landscape?.categories ?? [];
  const categoryMax = Math.max(...categories.map((item) => item.count), 1);

  return (
    <section className="government-panel" aria-labelledby="government-panel-title">
      <p className="eyebrow">For local government</p>
      <h3 id="government-panel-title">Planning context</h3>
      <p className="government-panel-intro">
        A current, evidence-backed view of community composition and the local business landscape.
      </p>
      <ul className="government-panel-list">
        {summary.available_views?.map((view) => <li key={view}>{view}</li>)}
      </ul>
      {(metrics.length > 0 || categories.length > 0) && (
        <div className="government-visuals">
          {metrics.length > 0 && (
            <section aria-labelledby="community-indicators-title">
              <h4 id="community-indicators-title">Community indicators</h4>
              <div className="government-bars">
                {metrics.map((metric) => (
                  <div className="government-bar-row" key={metric.key}>
                    <div className="government-bar-label">
                      <span>{metric.label}</span>
                      <strong>{metric.value.toFixed(1)}%</strong>
                    </div>
                    <div className="government-bar-track" aria-hidden="true">
                      <span style={{ width: `${Math.min(Math.max(metric.value, 0), 100)}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}
          {categories.length > 0 && (
            <section aria-labelledby="business-mix-title">
              <h4 id="business-mix-title">Mapped business mix</h4>
              <div className="government-bars">
                {categories.slice(0, 6).map((item) => (
                  <div className="government-bar-row" key={item.category}>
                    <div className="government-bar-label">
                      <span>{item.category}</span>
                      <strong>{item.count}</strong>
                    </div>
                    <div className="government-bar-track" aria-hidden="true">
                      <span style={{ width: `${(item.count / categoryMax) * 100}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>
      )}
      <p className="government-trend-note">
        Trends and displacement analysis require historical ACS vintages; this view shows the current snapshot only.
      </p>
      {summary.unavailable_views?.length > 0 && (
        <details>
          <summary>Not available from this dataset yet</summary>
          <ul className="government-panel-list muted">
            {summary.unavailable_views.map((view) => <li key={view}>{view}</li>)}
          </ul>
        </details>
      )}
    </section>
  );
}

export default GovernmentPlanningPanel;
