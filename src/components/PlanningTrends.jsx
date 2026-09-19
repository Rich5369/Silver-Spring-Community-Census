import { useId, useMemo, useState } from 'react';
import { buildLinearProjection, buildRangeProjection } from '../utils/projection';

const INTEGER = new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 });
const CURRENCY = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 });
const PERCENT = new Intl.NumberFormat('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 });

// A share is already a percentage, so a projection of one is bounded at both
// ends: a negative rate is impossible and one above 100% is not a rate at all.
const SHARE_BOUNDS = { maximum: 100 };

const formatValue = (value, format) => {
  if (format === 'currency') return CURRENCY.format(value);
  if (format === 'percent') return `${PERCENT.format(value)}%`;
  return INTEGER.format(value);
};

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

function Evidence({ source, geography, fallback, note }) {
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
  // A field the payload does not carry is left out rather than filled with a
  // placeholder, so nothing here reads as metadata the source did not supply.
  const fields = [
    ['Source organization', source.organization],
    ['Dataset', source.dataset],
    ['Releases', years.join(', ')],
    ['Geography', geography],
    ['Tracts aggregated', source.tract_count || ''],
    ['Table / variable', source.table],
  ].filter(([, value]) => value !== '' && value != null);
  return (
    <details className="trend-evidence-details">
      <summary><span>View evidence</span><small>{years.length} {years.length === 1 ? 'release' : 'releases'}</small></summary>
      <div className="trend-evidence-content">
        <p>{note ?? 'Every value below comes from the connected government trends data flow. Projected values are calculated in this browser from these displayed inputs.'}</p>
        <dl className="trend-evidence">
          {fields.map(([term, value]) => (
            <div key={term}><dt>{term}</dt><dd>{value}</dd></div>
          ))}
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

/**
 * Fold a snapshot indicator's per-variable evidence into one series source.
 *
 * A ratio metric cites both its numerator and its denominator, and both name
 * the same release, so the releases are keyed by year to keep `years` and
 * `urls` parallel for the evidence links.
 */
function indicatorSource(indicator) {
  const releases = new Map();
  (indicator.evidence ?? []).forEach((record) => {
    if (!releases.has(record.year)) releases.set(record.year, record.url);
  });
  const years = [...releases.keys()].sort((a, b) => a - b);
  const variables = [...new Set((indicator.evidence ?? []).map(({ variable }) => variable).filter(Boolean))];
  return {
    organization: indicator.evidence?.[0]?.organization ?? '',
    dataset: indicator.evidence?.[0]?.dataset ?? '',
    table: variables.join(', '),
    years,
    urls: years.map((year) => releases.get(year)).filter(Boolean),
    tract_count: indicator.tractCount,
  };
}

function MetricPanel({ metric, geography }) {
  const isRange = metric.series?.basis === 'range';
  const points = metric.series?.points ?? [];
  const bounds = metric.projectionBounds;
  const projection = useMemo(
    () => (isRange ? buildRangeProjection(points, bounds) : buildLinearProjection(points, bounds)),
    [isRange, points, bounds],
  );
  const historical = projection.historical;
  const source = metric.series?.source ?? null;
  const current = metric.current ?? null;
  const name = metric.metricName ? <p className="trend-metric-name">{metric.metricName}</p> : null;
  if (!historical.length) {
    // No series reaches the frontend for this metric, but the snapshot may
    // still carry its latest observed value. Showing that is better than an
    // empty panel, and it is labelled as a single release rather than a trend.
    return (
      <div className="trend-empty">
        {name}
        {current && (
          <div className="trend-summary">
            <div>
              <span>Current</span>
              <strong>{formatValue(current.value, metric.format)}</strong>
              {current.evidence?.[0]?.year && <small>{current.evidence[0].year} release</small>}
            </div>
          </div>
        )}
        <strong>{metric.unavailable}</strong>
        <p>Not enough historical data for a responsible projection.</p>
        {current?.formula && <p className="trend-note">{current.formula}</p>}
        <Evidence
          source={current ? indicatorSource(current) : source}
          geography={geography}
          fallback={metric.unavailable}
          note={current ? 'This value comes from the connected community snapshot. No historical series is published for this metric, so no projection is calculated.' : undefined}
        />
      </div>
    );
  }
  const first = historical[0];
  const last = historical.at(-1);
  // A metric already expressed as a percentage moves in percentage points.
  // Reporting its change as a percent would describe a percentage of a
  // percentage - a different quantity, and one that reads far larger.
  const isShare = metric.format === 'percent';
  const changeFor = (edge) => {
    const from = edge ? first[edge] : first.value;
    const to = edge ? last[edge] : last.value;
    if (isShare) return to - from;
    return from === 0 ? null : ((to - from) / Math.abs(from)) * 100;
  };
  const percent = (value) => (value == null
    ? 'Not available'
    : `${value >= 0 ? '+' : ''}${value.toFixed(1)}${isShare ? ' pp' : '%'}`);
  const change = isRange
    ? `${percent(changeFor('low'))} / ${percent(changeFor('high'))}`
    : percent(changeFor(null));
  return (
    <div className="trend-content">
      {name}
      <div className="trend-summary">
        <div>
          <span>{isRange ? 'Current range' : 'Current'}</span>
          <strong>{formatPoint(last, metric.format, isRange)}</strong>
          <small>{last.year} release</small>
        </div>
        <div>
          <span>Historical change</span>
          <strong>{change}</strong>
          <small>{isShare ? 'percentage points ' : ''}over {historical.length} releases{isRange ? ', low / high' : ''}</small>
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
          The dashed values cover {last.year + 1}–{last.year + 5}, are constrained to the valid range
          for this metric{isShare ? ' (0–100%)' : ' (non-negative)'}, and are a planning aid—not an
          official government forecast. Three overlapping ACS
          releases is a thin basis for a five-year projection; treat it as directional only.
        </p>
      </details>
    </div>
  );
}

export default function PlanningTrends({ insights, trends, trendGeography = '', onExploreMap }) {
  const [open, setOpen] = useState(null);
  const baseId = useId();
  const geography = insights?.areaName || 'Selected community';
  const normalizedName = (value) => String(value || '').trim().toLocaleLowerCase();
  const sameStudyArea = Boolean(trendGeography) && normalizedName(geography) === normalizedName(trendGeography);
  const series = sameStudyArea ? (trends?.series ?? []) : [];
  const findSeries = (keys) => series.find((item) => keys.includes(item.key));
  // Indicators travel with the profile whose name is shown above, so they need
  // no geography check of their own: a selected tract carries none, exactly as
  // the study-area series are withheld for a tract.
  const indicators = insights?.indicators ?? {};
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
    {
      id: 'housing',
      label: 'Housing costs',
      format: 'percent',
      // The connected ACS data carries no median gross rent or median monthly
      // housing cost, so rent burden is the supported cost measure. Its exact
      // threshold is named here because "housing costs" alone would not say
      // which quantity the number is.
      metricName: 'Renter households spending 35% or more of income on gross rent',
      series: findSeries(['rent_burden_share']),
      current: indicators.rent_burden_share ?? null,
      projectionBounds: SHARE_BOUNDS,
      unavailable: 'Historical trend unavailable for this metric.',
    },
    {
      id: 'unemployment',
      label: 'Unemployment',
      format: 'percent',
      metricName: 'Unemployment rate among the civilian labor force',
      series: findSeries(['unemployment_rate']),
      current: indicators.unemployment_rate ?? null,
      projectionBounds: SHARE_BOUNDS,
      unavailable: 'Historical trend unavailable for this metric.',
    },
  ];
  return (
    <section className="planning-trends" id="planning-trends" aria-labelledby={`${baseId}-title`}>
      <div className="planning-trends-heading">
        <div><h2 id={`${baseId}-title`}>Community Trends &amp; Outlook</h2></div>
        <p><strong>{geography}</strong><span>Montgomery County, Maryland</span></p>
      </div>
      <p className="planning-trends-intro">Explore how key community indicators are changing over time using verified public data and transparent trend-based projections.</p>
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
      </div>
      <details className="trend-disclosure about-trend">
        <summary>About this trend</summary>
        <p>
          Consecutive American Community Survey 5-Year Estimates contain overlapping survey periods.
          Treat changes as directional planning indicators, not independent year-by-year measurements.
          Metrics are shown only for matching geographic definitions.
        </p>
      </details>
      <div className="trend-map-action">
        <button className="secondary-button" type="button" onClick={onExploreMap}>Explore this area on the map</button>
      </div>
    </section>
  );
}
