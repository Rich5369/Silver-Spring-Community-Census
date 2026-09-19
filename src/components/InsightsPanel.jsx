import EvidenceDetails from './EvidenceDetails';
import ComparisonPanel from './ComparisonPanel';
import StatCard from './StatCard';
import AboutData from './AboutData';
import { fentonVillageInsights } from '../data/communityInsights';
import { isDemoStatus } from '../services/provenance';
import OpportunityExplorer from './OpportunityExplorer';
import GovernmentPlanningPanel from './GovernmentPlanningPanel';

function InsightsPanel({
  insights = fentonVillageInsights,
  comparisonAreas = [],
  businesses = [],
  governmentSummary = null,
  isAreaSelected = false,
  hasQueryResult = false,
}) {
  const selectedInsights = insights ?? fentonVillageInsights;
  const stats = Array.isArray(selectedInsights.stats) ? selectedInsights.stats : [];
  const sources = Array.isArray(selectedInsights.sources) ? selectedInsights.sources : [];
  const isDemo = isDemoStatus(selectedInsights.dataStatus);
  const showSummary = isAreaSelected || !hasQueryResult;
  const summaryStats = stats.slice(0, isAreaSelected ? 2 : 3);

  return (
    <section className="community-context" aria-labelledby="community-context-title">
      {showSummary && (
        <div className="community-context-summary">
          <div className="context-heading">
            <div>
              <p className="eyebrow">{isAreaSelected ? 'Selected area' : 'Community context'}</p>
              <h2 id="community-context-title">{selectedInsights.areaName || 'Selected community'}</h2>
              <p>{selectedInsights.summary || 'Community details are not available yet.'}</p>
            </div>
            <span className="demo-data-status">
              {selectedInsights.dataStatus || 'Data status not available'}
            </span>
          </div>
          <div className="context-stat-grid">
            {summaryStats.map((stat, index) => (
              <StatCard
                key={stat.id || `summary-stat-${index}`}
                {...stat}
                sources={sources.filter((source) => stat.sourceIds?.includes(source.id))}
              />
            ))}
            {summaryStats.length === 0 && <p className="empty-data-message">No statistics available.</p>}
          </div>
        </div>
      )}

      <details className="community-context-more">
        <summary>{showSummary ? 'View more community details' : `View ${selectedInsights.areaName || 'community'} context`}</summary>
        <div className="community-context-details">
          {!showSummary && (
            <div className="context-heading">
              <div>
                <p className="eyebrow">Community context</p>
                <h2 id="community-context-title">{selectedInsights.areaName || 'Selected community'}</h2>
                <p>{selectedInsights.summary || 'Community details are not available yet.'}</p>
              </div>
              <span className="demo-data-status">
                {selectedInsights.dataStatus || 'Data status not available'}
              </span>
            </div>
          )}

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

          <OpportunityExplorer insights={selectedInsights} businesses={businesses} />
          <GovernmentPlanningPanel summary={governmentSummary} />

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

          <AboutData />
          {comparisonAreas.length > 1 && <ComparisonPanel areas={comparisonAreas} />}
        </div>
      </details>
    </section>
  );
}

export default InsightsPanel;
