function StatCard({ label, value, note }) {
  const displayValue = value == null || (typeof value === 'number' && !Number.isFinite(value))
    ? '—'
    : value;

  return (
    <article className="stat-card">
      <span>{label || 'Community indicator'}</span>
      <strong>{displayValue}</strong>
      <small>{note || 'Details not available'}</small>
    </article>
  );
}

export default StatCard;
