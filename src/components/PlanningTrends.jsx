import { useId, useMemo, useState } from 'react';
import { buildLinearProjection, buildRangeProjection } from '../utils/projection';

const INTEGER = new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 });
const CURRENCY = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 });

const formatValue = (value, format) => (format === 'currency' ? CURRENCY : INTEGER).format(value);

/** A range point renders as "low – high"; a total renders as one number. */
const formatPoint = (point, format, isRange) => (isRange
  ? `${formatValue(point.low, format)} – ${formatValue(point.high, format)}`
  : formatValue(point.value, format));

function TrendChart({ label, historical, projected, isRange }) {
  const all = [...historical, ...projected];
  const numbers = all.flatMap((point) => (isRange ? [point.low, point.high] : [point.value]));
  const min = Math.min(...numbers);
  const max = Math.max(...numbers);
  const span = max - min || 1;
  const firstYear = Math.min(...all.map(({ year }) => year));
  const lastYear = Math.max(...all.map(({ year }) => year));
  const yearSpan = lastYear - firstYear || 1;
  const x = (year) => 28 + (((year - firstYear) / yearSpan) * 544);
  const y = (value) => 154 - (((value - min) / span) * 112);
  const path = (points, edge) => points
    .map((point, index) => `${index ? 'L' : 'M'} ${x(point.year)} ${y(edge ? point[edge] : point.value)}`)
    .join(' ');
  // The projected path starts at the last historical point so the dashed
  // segment visibly continues the solid one rather than floating free.
  const withJoin = (points, edge) => (points.length ? path([historical.at(-1), ...points], edge) : '');
  const edges = isRange ? ['low', 'high'] : [null];
  const band = (points, edge) => points.map((point) => `${x(point.year)},${y(point[edge])}`).join(' ');
  return (
    <div className="trend-chart-wrap">
      <svg className="trend-chart" viewBox="0 0 600 190" role="img" aria-label={`${label} historical and projected trend`}>
        {isRange && (
          <polygon
            className="trend-band"
            points={`${band(historical, 'high')} ${band([...historical].reverse(), 'low')}`}
          />
        )}
        {edges.map((edge) => (
          <g key={edge ?? 'value'}>
            <path className="trend-line historical" d={path(historical, edge)} />
            {projected.length > 0 && <path className="trend-line projected" d={withJoin(projected, edge)} />}
          </g>
        ))}
        {all.map((point, index) => edges.map((edge) => (
          <circle
            key={`${point.year}-${edge ?? 'value'}`}
            className={index < historical.length ? 'historical-dot' : 'projected-dot'}
            cx={x(point.year)}
            cy={y(edge ? point[edge] : point.value)}
            r="5"
          />
        )))}
        {all.map((point) => (
          <text key={`label-${point.year}`} x={x(point.year)} y="179" textAnchor="middle">{point.year}</text>
        ))}
      </svg>
      <div className="trend-legend" aria-hidden="true">
        <span><i className="historical-dot" /> Historical</span>
        <span><i className="projected-dot" /> Projected</span>
        {isRange && <span><i className="band-swatch" /> Range across tracts</span>}
      </div>
    </div>
  );
}

function Evidence({ source, geography, fallback }) {
  if (!source) {
    return (
      <details className="trend-evidence-details">
        <summary><span>View evidence</span><small>no matching source</small></summary>
        <div className="trend-evidence-content">
          <p>{fallback}</p>
          <dl className="trend-evidence">
            <div><dt>Geography</dt><dd>{geography}</dd></div>
            <div><dt>Status</dt><dd>No source metadata was returned for this metric.</dd></div>
          </dl>
        </div>
      </details>
    );
  }
  const years = source.years ?? [];
  const urls = source.urls ?? [];
  return (
    <details className="trend-evidence-details">
      <summary><span>View evidence</span><small>{years.length} historical {years.length === 1 ? 'release' : 'releases'}</small></summary>
      <div className="trend-evidence-content">
        <p>Every value below comes from the connected government trends data flow. Projected values are calculated in this browser from these displayed inputs.</p>
        <dl className="trend-evidence">
          <div><dt>Source organization</dt><dd>{source.organization || 'Not provided'}</dd></div>
          <div><dt>Dataset</dt><dd>{source.dataset || 'Not provided'}</dd></div>
          <div><dt>Historical releases</dt><dd>{years.join(', ') || 'Not provided'}</dd></div>
          <div><dt>Geography</dt><dd>{geography}</dd></div>
          <div><dt>Tracts aggregated</dt><dd>{source.tract_count || 'Not provided'}</dd></div>
          <div><dt>Table / variable</dt><dd>{source.table || 'Not provided'}</dd></div>
        </dl>
        {urls.length > 0 && (
          <ul className="trend-evidence-links">
            {urls.map((url, index) => (
              <li key={url}><a href={url} target="_blank" rel="noreferrer">{years[index] ?? 'Release'} source</a></li>
            ))}
          </ul>
        )}
      </div>
    </details>
  );
}

function MetricPanel({ metric, geography }) {
  const isRange = metric.series?.basis === 'range';
  const points = metric.series?.points ?? [];
  const projection = useMemo(
    () => (isRange ? buildRangeProjection(points) : buildLinearProjection(points)),
    [isRange, points],
  );
  const historical = projection.historical;
  const source = metric.series?.source ?? null;
  if (!historical.length) {
    return (
      <div className="trend-empty">
        <strong>{metric.unavailable}</strong>
        <p>Not enough historical data for a responsible projection.</p>
        <Evidence source={source} geography={geography} fallback={metric.unavailable} />
      </div>
    );
  }
  const first = historical[0];
  const last = historical.at(-1);
  const changeFor = (edge) => {
    const from = edge ? first[edge] : first.value;
    const to = edge ? last[edge] : last.value;
    return from === 0 ? null : ((to - from) / Math.abs(from)) * 100;
  };
  const percent = (value) => (value == null ? 'Not available' : `${value >= 0 ? '+' : ''}${value.toFixed(1)}%`);
  const change = isRange
    ? `${percent(changeFor('low'))} / ${percent(changeFor('high'))}`
    : percent(changeFor(null));
  return (
    <div className="trend-content">
      <div className="trend-summary">
        <div>
          <span>{isRange ? 'Current range' : 'Current'}</span>
          <strong>{formatPoint(last, metric.format, isRange)}</strong>
          <small>{last.year} release</small>
        </div>
        <div>
          <span>Historical change</span>
          <strong>{change}</strong>
          <small>over {historical.length} releases{isRange ? ', low / high' : ''}</small>
        </div>
        <div>
          <span>5-year trend-based projection</span>
          <strong>{projection.status === 'available' ? formatPoint(projection.projected.at(-1), metric.format, isRange) : 'Not available'}</strong>
        </div>
      </div>
      <TrendChart label={metric.label} historical={historical} projected={projection.projected} isRange={isRange} />
      {projection.status === 'insufficient' && <p className="trend-warning">Not enough historical data for a responsible projection.</p>}
      {projection.status === 'unstable' && <p className="trend-warning">Trend too unstable for a useful projection.</p>}
      {metric.series?.method && <p className="trend-note">{metric.series.method}</p>}
      <div className="trend-table-wrap">
        <table>
          <caption>Exact values used in this trend</caption>
          <thead>
            <tr>
              <th>Year</th>
              <th>Status</th>
              {isRange ? <><th>Low</th><th>High</th></> : <th>Value</th>}
            </tr>
          </thead>
          <tbody>
            {[
              ...historical.map((point) => ({ ...point, status: 'Historical' })),
              ...projection.projected.map((point) => ({ ...point, status: 'Projected' })),
            ].map((point) => (
              <tr key={`${point.status}-${point.year}`}>
                <th scope="row">{point.year}</th>
                <td>{point.status}</td>
                {isRange
                  ? <><td>{formatValue(point.low, metric.format)}</td><td>{formatValue(point.high, metric.format)}</td></>
                  : <td>{formatValue(point.value, metric.format)}</td>}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Evidence source={source} geography={geography} fallback={metric.unavailable} />
      <details className="trend-disclosure">
        <summary>How is this projection calculated?</summary>
        <p>
          The {historical.length} observations from {first.year}–{last.year} are fitted with ordinary
          least-squares linear regression{isRange ? ', with the low and high edges fitted separately' : ''}.
          The dashed values cover {last.year + 1}–{last.year + 5}, are constrained to valid non-negative
          values, and are a planning aid—not an official government forecast. Three overlapping ACS
          releases is a thin basis for a five-year projection; treat it as directional only.
        </p>
      </details>
    </div>
  );
}

function ServiceRequestPanel({ data }) {
  const points = data?.series ?? [];
  const max = Math.max(...points.map((point) => point.requests), 1);
  const first = points[0]?.requests;
  const last = points.at(-1)?.requests;
  const change = first ? ((last - first) / first) * 100 : null;
  return (
    <div className="trend-content">
      <div className="trend-summary">
        <div><span>Latest annual volume</span><strong>{last?.toLocaleString() ?? 'Unavailable'}</strong><small>{points.at(-1)?.year ?? ''}</small></div>
        <div><span>Change since first release</span><strong>{change == null ? 'Unavailable' : (change >= 0 ? '+' : '') + change.toFixed(1) + '%'}</strong><small>directional screening signal</small></div>
        <div><span>Source status</span><strong>{data?.source_status === 'live' ? 'Live' : 'Snapshot'}</strong><small>Montgomery County MC311</small></div>
      </div>
      <div className="service-request-bars" role="img" aria-label="Annual Montgomery County service request counts for ZIP 20910">
        {points.map((point) => <div className="service-request-bar" key={point.year}><span style={{ height: Math.max(4, (point.requests / max) * 100) + '%' }} title={point.year + ': ' + point.requests.toLocaleString() + ' requests'} /><small>{point.year}</small></div>)}
      </div>
      <p className="trend-note">Official MC311 requests for ZIP 20910, a broader screening geography than Fenton Village. Volume does not prove unmet need, service quality, or causation.</p>
      <details className="trend-evidence-details"><summary><span>View official source</span><small>Montgomery County</small></summary><div className="trend-evidence-content"><p>{(data?.limitations ?? []).join(' ')}</p>{data?.evidence?.map((item) => <a key={item.source_url} href={item.source_url} target="_blank" rel="noreferrer">{item.organization}: {item.dataset}</a>)}</div></details>
    </div>
  );
}

export default function PlanningTrends({ insights, trends, serviceRequests, trendGeography = '' }) {
  const [open, setOpen] = useState(null);
  const baseId = useId();
  const geography = insights?.areaName || 'Selected community';
  const normalizedName = (value) => String(value || '').trim().toLocaleLowerCase();
  const sameStudyArea = Boolean(trendGeography) && normalizedName(geography) === normalizedName(trendGeography);
  const series = sameStudyArea ? (trends?.series ?? []) : [];
  const findSeries = (keys) => series.find((item) => keys.includes(item.key));
  const metrics = [
    {
      id: 'population',
      label: 'Population',
      series: findSeries(['total_population', 'population']),
      unavailable: 'Historical trend unavailable for this metric.',
    },
    {
      id: 'income',
      label: 'Median household income',
      format: 'currency',
      series: findSeries(['median_household_income']),
      unavailable: 'Historical trend unavailable for this metric.',
    },
  ];
  return (
    <section className="planning-trends" id="planning-trends" aria-labelledby={`${baseId}-title`}>
      <div className="planning-trends-heading">
        <div><p className="eyebrow">For city planners</p><h2 id={`${baseId}-title`}>Planning Trends</h2></div>
        <p><strong>{geography}</strong><span>Montgomery County, Maryland</span></p>
      </div>
      <p className="planning-trends-intro">Recent verified releases and transparent planning projections, when enough comparable history exists.</p>
      <div className="trend-accordions">
          {metrics.map((metric) => {
          const expanded = open === metric.id;
          const panelId = `${baseId}-${metric.id}`;
          return (
            <div className="trend-accordion" key={metric.id}>
              <button type="button" aria-expanded={expanded} aria-controls={panelId} onClick={() => setOpen(expanded ? null : metric.id)}>
                <span aria-hidden="true">{expanded ? '▾' : '▸'}</span>{metric.label}
              </button>
              <div id={panelId} hidden={!expanded}><MetricPanel metric={metric} geography={geography} /></div>
            </div>
          );
          })}
        {serviceRequests?.series?.length > 1 && (
          <div className="trend-accordion">
            <button type="button" aria-expanded={open === 'service-requests'} onClick={() => setOpen(open === 'service-requests' ? null : 'service-requests')}><span aria-hidden="true">{open === 'service-requests' ? '▾' : '▸'}</span>Official service-request volume</button>
            <div hidden={open !== 'service-requests'}><ServiceRequestPanel data={serviceRequests} /></div>
          </div>
        )}
      </div>
      <details className="trend-disclosure about-trend">
        <summary>About this trend</summary>
        <p>
          Consecutive American Community Survey 5-Year Estimates contain overlapping survey periods.
          Treat changes as directional planning indicators, not independent year-by-year measurements.
          Metrics are shown only for matching geographic definitions.
        </p>
      </details>
    </section>
  );
}
