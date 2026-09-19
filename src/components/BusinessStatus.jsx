import { isDemoBusiness } from '../services/provenance';

export default function BusinessStatus({ business, sources = [] }) {
  const isDemo = isDemoBusiness(business, sources);

  return (
    <p className={isDemo ? 'business-status demo' : 'business-status'}>
      {/* The warning symbol keeps the demo label readable without relying on the yellow tint. */}
      {isDemo ? <span aria-hidden="true">⚠ </span> : null}
      {isDemo ? 'Demo / mock data — not verified' : `Source: ${business.source || 'Not provided'}`}
    </p>
  );
}
