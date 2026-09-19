import { insightCards } from '../data/placeholderData';

function InsightsPanel() {
  return (
    <aside className="insights-panel">
      <div className="panel-heading">
        <p className="eyebrow">Selected area</p>
        <h2>Community insights</h2>
        <p>Choose a neighborhood or map feature to explore local context.</p>
      </div>

      <div className="insight-list">
        {insightCards.map(({ label, value, detail }) => (
          <article className="insight-card" key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
            <p>{detail}</p>
          </article>
        ))}
      </div>

      <div className="evidence-note">
        <span aria-hidden="true">↗</span>
        <div>
          <strong>Evidence first</strong>
          <p>Every published insight will link to its source and collection date.</p>
        </div>
      </div>
    </aside>
  );
}

export default InsightsPanel;
