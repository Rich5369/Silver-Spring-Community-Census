import EvidenceDetails from './EvidenceDetails';
import StatCard from './StatCard';
import { fentonVillageInsights } from '../data/communityInsights';

function InsightsPanel({ insights = fentonVillageInsights }) {
  const selectedInsights = insights ?? fentonVillageInsights;
  const stats = Array.isArray(selectedInsights.stats) ? selectedInsights.stats : [];
  const sources = Array.isArray(selectedInsights.sources) ? selectedInsights.sources : [];
  const isDemo = /demo|mock|illustrative/i.test(selectedInsights.dataStatus || '');

  return (
    <aside className="insights-panel" aria-labelledby="insights-title">
      <div className="panel-heading">
        <p className="eyebrow">Selected area</p>
        <h2 id="insights-title">{selectedInsights.areaName || 'Selected community'}</h2>
        <p>{selectedInsights.summary || 'Community details are not available yet.'}</p>
        <span className="demo-data-status">
          {selectedInsights.dataStatus || 'Data status not available'}
        </span>
      </div>

      <section className="insights-section" aria-labelledby="community-stats-title">
        <h3 id="community-stats-title">Community snapshot</h3>
        <div className="stat-grid">
          {stats.map((stat, index) => (
            <StatCard
              key={stat.id || `stat-${index}`}
              {...stat}
              sources={sources.filter((source) => stat.sourceIds?.includes(source.id))}
            />
          ))}
          {stats.length === 0 && <p className="empty-data-message">No statistics available.</p>}
        </div>
      </section>

      <section className="evidence-section" aria-labelledby="evidence-title">
        <div className="section-heading">
          <h3 id="evidence-title">Evidence &amp; Sources</h3>
          <span>{isDemo ? 'Demo only' : 'Sources'}</span>
        </div>
        <p className="source-intro">
          {isDemo
            ? 'No verified Census source is connected yet. Future records will identify the dataset, year, geography, table, and source link.'
            : 'Source records identify the organization, dataset, year, geography, table, and original link.'}
        </p>
        <div className="source-list">
          <EvidenceDetails sources={sources} label="Browse all evidence" />
        </div>
      </section>
    </aside>
  );
}

export default InsightsPanel;
