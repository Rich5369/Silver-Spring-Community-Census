import SourceCard from './SourceCard';

function EvidenceDetails({ sources = [], label = 'Evidence' }) {
  return (
    <details className="evidence-details">
      <summary>
        <span>{label}</span>
        <small>{sources.length} {sources.length === 1 ? 'source' : 'sources'}</small>
      </summary>
      <div className="evidence-details-content">
        {sources.map((source, index) => (
          <SourceCard key={source.id || `${source.organization || 'source'}-${index}`} source={source} />
        ))}
        {sources.length === 0 && (
          <p className="empty-data-message">No source metadata is available.</p>
        )}
      </div>
    </details>
  );
}

export default EvidenceDetails;
