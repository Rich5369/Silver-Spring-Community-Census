import { useId, useMemo, useState } from 'react';
import { buildLinearProjection } from '../utils/projection';

const INTEGER = new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 });
const CURRENCY = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 });

const formatValue = (value, format) => (format === 'currency' ? CURRENCY : INTEGER).format(value);

function TrendChart({ label, historical, projected, format }) {
  const all = [...historical, ...projected];
  const min = Math.min(...all.map(({ value }) => value));
  const max = Math.max(...all.map(({ value }) => value));
  const span = max - min || 1;
  const firstYear = Math.min(...all.map(({ year }) => year));
  const lastYear = Math.max(...all.map(({ year }) => year));
  const yearSpan = lastYear - firstYear || 1;
  const x = (year) => 28 + (((year - firstYear) / yearSpan) * 544);
  const y = (value) => 154 - (((value - min) / span) * 112);
  const historicalPath = historical.map((point, index) => `${index ? 'L' : 'M'} ${x(point.year)} ${y(point.value)}`).join(' ');
  const projectedPath = projected.length
    ? [historical.at(-1), ...projected].map((point, index) => `${index ? 'L' : 'M'} ${x(point.year)} ${y(point.value)}`).join(' ')
    : '';
  return (
    <div className="trend-chart-wrap">
      <svg className="trend-chart" viewBox="0 0 600 190" role="img" aria-label={`${label} historical and projected trend`}>
        <path className="trend-line historical" d={historicalPath} />
        {projectedPath && <path className="trend-line projected" d={projectedPath} />}
        {all.map((point, index) => (
          <g key={`${point.year}-${index}`}>
            <circle className={index < historical.length ? 'historical-dot' : 'projected-dot'} cx={x(point.year)} cy={y(point.value)} r="5" />
            <text x={x(point.year)} y="179" textAnchor="middle">{point.year}</text>
          </g>
        ))}
      </svg>
      <div className="trend-legend" aria-hidden="true"><span><i className="historical-dot" /> Historical</span><span><i className="projected-dot" /> Projected</span></div>
    </div>
  );
}

function Evidence({ source, years, geography }) {
  if (!source) return <p className="trend-note">Source evidence for this metric is not available.</p>;
  return (
    <details className="trend-evidence-details">
      <summary><span>View evidence</span><small>{years.length} historical {years.length === 1 ? 'release' : 'releases'}</small></summary>
      <div className="trend-evidence-content">
        <p>The historical values and release years below are returned by the connected government trends data flow. Projected values are calculated in this browser from those displayed inputs.</p>
        <dl className="trend-evidence">
          <div><dt>Source organization</dt><dd>{source.organization || 'Not provided'}</dd></div>
          <div><dt>Dataset</dt><dd>{/acs|american community survey/i.test(`${source.dataset} ${source.organization}`) ? 'American Community Survey 5-Year Estimates' : source.dataset || 'Not provided'}</dd></div>
          <div><dt>Historical releases</dt><dd>{years.join(', ')}</dd></div>
          <div><dt>Geography</dt><dd>{geography}</dd></div>
          <div><dt>Table / field</dt><dd>{source.table || 'Not provided'}</dd></div>
          {source.url && <div><dt>Original source</dt><dd><a href={source.url} target="_blank" rel="noreferrer">Open original source</a></dd></div>}
        </dl>
        <p className="trend-evidence-caveat">The source metadata currently supplies one original-source link for the metric, not a separate link for every historical vintage. The exact values used are preserved in the table above.</p>
      </div>
    </details>
  );
}

function MetricPanel({ metric, geography }) {
  const projection = useMemo(() => buildLinearProjection(metric.points), [metric.points]);
  const historical = projection.historical;
  if (!historical.length) {
    return <div className="trend-empty"><strong>{metric.unavailable}</strong>{metric.current != null && <p>{metric.currentLabel || 'Current verified value'}: {formatValue(metric.current, metric.format)}</p>}<p>Not enough historical data for a responsible projection.</p></div>;
  }
  const first = historical[0];
  const last = historical.at(-1);
  const change = first.value === 0 ? null : ((last.value - first.value) / Math.abs(first.value)) * 100;
  return (
    <div className="trend-content">
      <div className="trend-summary">
        <div><span>Current</span><strong>{formatValue(last.value, metric.format)}</strong></div>
        <div><span>Historical change</span><strong>{change == null ? 'Not available' : `${change >= 0 ? '+' : ''}${change.toFixed(1)}%`}</strong><small>over {historical.length} releases</small></div>
        <div><span>5-year trend-based projection</span><strong>{projection.status === 'available' ? formatValue(projection.projected.at(-1).value, metric.format) : 'Not available'}</strong></div>
      </div>
      <TrendChart label={metric.label} historical={historical} projected={projection.projected} format={metric.format} />
      {projection.status === 'insufficient' && <p className="trend-warning">Not enough historical data for a responsible projection.</p>}
      {projection.status === 'unstable' && <p className="trend-warning">Trend too unstable for a useful projection.</p>}
      <div className="trend-table-wrap"><table><caption>Exact values used in this trend</caption><thead><tr><th>Year</th><th>Status</th><th>Value</th></tr></thead><tbody>{[...historical.map((p) => ({ ...p, status: 'Historical' })), ...projection.projected.map((p) => ({ ...p, status: 'Projected' }))].map((point) => <tr key={`${point.status}-${point.year}`}><th scope="row">{point.year}</th><td>{point.status}</td><td>{formatValue(point.value, metric.format)}</td></tr>)}</tbody></table></div>
      <Evidence source={metric.source} years={historical.map(({ year }) => year)} geography={geography} />
      <details className="trend-disclosure"><summary>How is this projection calculated?</summary><p>The {historical.length} observations from {first.year}–{last.year} are fitted with ordinary least-squares linear regression. The dashed values cover {last.year + 1}–{last.year + 5}, are constrained to valid non-negative values, and are a planning aid—not an official government forecast.</p></details>
    </div>
  );
}

export default function PlanningTrends({ insights, trends, trendGeography = '', businessCount = 0 }) {
  const [open, setOpen] = useState(null);
  const baseId = useId();
  const geography = insights?.areaName || 'Selected community';
  const sources = insights?.sources ?? [];
  const normalizedName = (value) => String(value || '').trim().toLocaleLowerCase();
  const sameStudyArea = Boolean(trendGeography) && normalizedName(geography) === normalizedName(trendGeography);
  const series = sameStudyArea ? (trends?.series ?? []) : [];
  const findSeries = (keys) => series.find((item) => keys.includes(item.key));
  const population = findSeries(['total_population', 'population']);
  const currentIncome = insights?.stats?.find((stat) => ['income', 'median_household_income'].includes(stat.id))?.rawValue;
  const populationSource = sources.find((source) => /population|B01003/i.test(`${source.table} ${source.dataset}`)) ?? sources.find((source) => /census|acs|american community survey/i.test(`${source.organization} ${source.dataset}`));
  const verifiedPopulation = populationSource ? population : null;
  const metrics = [
    { id: 'population', label: 'Population', points: verifiedPopulation?.points ?? [], source: populationSource, unavailable: 'Historical population trend unavailable for this geography with verifiable source metadata' },
    { id: 'income', label: 'Median household income', format: 'currency', points: [], current: currentIncome, unavailable: 'Historical median household income trend unavailable' },
    { id: 'housing', label: 'Housing costs', format: 'currency', points: [], unavailable: 'Historical housing-cost trend unavailable' },
    { id: 'businesses', label: 'Local businesses', points: [], current: businessCount, currentLabel: 'Current verified mapped count for the study area', unavailable: 'Historical business trend unavailable' },
  ];
  return (
    <section className="planning-trends" aria-labelledby={`${baseId}-title`}>
      <div className="planning-trends-heading"><div><p className="eyebrow">For city planners</p><h2 id={`${baseId}-title`}>Planning Trends</h2></div><p><strong>{geography}</strong><span>Montgomery County, Maryland</span></p></div>
      <p className="planning-trends-intro">Recent verified releases and transparent planning projections, when enough comparable history exists.</p>
      <div className="trend-accordions">{metrics.map((metric) => { const expanded = open === metric.id; const panelId = `${baseId}-${metric.id}`; return <div className="trend-accordion" key={metric.id}><button type="button" aria-expanded={expanded} aria-controls={panelId} onClick={() => setOpen(expanded ? null : metric.id)}><span aria-hidden="true">{expanded ? '▾' : '▸'}</span>{metric.label}</button><div id={panelId} hidden={!expanded}><MetricPanel metric={metric} geography={geography} /></div></div>; })}</div>
      <details className="trend-disclosure about-trend"><summary>About this trend</summary><p>Consecutive American Community Survey 5-Year Estimates contain overlapping survey periods. Treat changes as directional planning indicators, not independent year-by-year measurements. Metrics are shown only for matching geographic definitions.</p></details>
    </section>
  );
}
