import { isDemoStatus } from '../services/provenance';

function SourceCard({ source = {} }) {
  const fallback = 'Not provided';
  const isDemo = isDemoStatus(
    `${source.organization || ''} ${source.dataset || ''} ${source.year || ''}`,
  );
  let sourceUrl = null;

  try {
    const parsedUrl = new URL(source.url);
    if (parsedUrl.protocol === 'http:' || parsedUrl.protocol === 'https:') {
      sourceUrl = parsedUrl.href;
    }
  } catch {
    sourceUrl = null;
  }

  return (
    <article className="source-card">
      {isDemo && <span className="source-status">Demo data</span>}
      <strong>{source.organization || 'Source pending'}</strong>
      <span>{source.dataset || 'Dataset not provided'}</span>
      <dl>
        <div>
          <dt>Year</dt>
          <dd>{source.year || fallback}</dd>
        </div>
        <div>
          <dt>Geography</dt>
          <dd>{source.geography || fallback}</dd>
        </div>
        <div>
          <dt>Table</dt>
          <dd>{source.table || fallback}</dd>
        </div>
      </dl>
      {sourceUrl && (
        <a href={sourceUrl} target="_blank" rel="noreferrer">
          View Source
        </a>
      )}
    </article>
  );
}

export default SourceCard;
