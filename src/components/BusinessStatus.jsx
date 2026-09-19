export default function BusinessStatus({ business, sources = [] }) {
  const isDemo = /demo|mock|illustrative/i.test(
    `${business.source || ''} ${sources.map((source) => `${source.organization} ${source.dataset}`).join(' ')}`,
  );
  return (
    <p className={isDemo ? 'business-status demo' : 'business-status'}>
      {/* The warning symbol keeps the demo label readable without relying on the yellow tint. */}
      {isDemo ? <span aria-hidden="true">⚠ </span> : null}
      {isDemo ? 'Demo / mock data — not verified' : `Source: ${business.source || 'Not provided'}`}
    </p>
  );
}
