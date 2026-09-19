function SourceCard({ source = {} }) {
  const fallback = 'Not provided';

  return (
    <article className="source-card">
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
      {source.url && (
        <a href={source.url} target="_blank" rel="noreferrer">
          View source
        </a>
      )}
    </article>
  );
}

export default SourceCard;
