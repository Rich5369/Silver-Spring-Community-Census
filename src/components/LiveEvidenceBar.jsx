function LiveEvidenceBar({ data, status, usingFallback }) {
  const tractCount = data.communityGeoJson?.features?.length ?? 0;
  const sourceCount = data.profile?.sources?.length ?? 0;
  const label = status === 'loading' ? 'Connecting to public data…' : usingFallback ? 'Demo data mode' : 'Connected to public data';
  return (
    <section className="evidence-bar" aria-label="Data coverage at a glance">
      <div className="evidence-bar-status"><span className={`status-pulse ${status === 'error' ? 'offline' : ''}`} />{label}</div>
      <div className="evidence-bar-stats">
        <div><b className="evidence-icon" aria-hidden="true">◎</b><strong>{tractCount || '—'}</strong><span>Census areas</span></div>
        <div><b className="evidence-icon" aria-hidden="true">⌖</b><strong>{data.businesses.length || '—'}</strong><span>Mapped places</span></div>
        <div><b className="evidence-icon" aria-hidden="true">◈</b><strong>{sourceCount || '—'}</strong><span>Evidence sources</span></div>
      </div>
      <p>Every headline number links back to its public source.</p>
    </section>
  );
}

export default LiveEvidenceBar;
