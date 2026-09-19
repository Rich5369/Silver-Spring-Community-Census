function GovernmentPlanningPanel({ summary }) {
  if (!summary) return null;

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
