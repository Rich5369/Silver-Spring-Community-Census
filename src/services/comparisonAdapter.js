const priorityMetrics = ['population', 'income', 'businesses', 'language'];

const isAvailable = (value) => (
  value !== null
  && value !== undefined
  && value !== ''
  && value !== '—'
  && value !== 'Data unavailable'
);

const metricMap = (area) => new Map(
  (Array.isArray(area?.stats) ? area.stats : []).map((stat) => [stat.id, stat]),
);

export function getComparisonAreaId(area) {
  return String(area?.areaId ?? area?.areaName ?? 'unnamed-area');
}

export function buildComparisonRows(leftArea, rightArea) {
  if (!leftArea || !rightArea) return [];

  const leftMetrics = metricMap(leftArea);
  const rightMetrics = metricMap(rightArea);
  const allMetricIds = new Set([...leftMetrics.keys(), ...rightMetrics.keys()]);
  const orderedIds = [
    ...priorityMetrics.filter((id) => allMetricIds.has(id)),
    ...[...allMetricIds].filter((id) => !priorityMetrics.includes(id)),
  ];

  return orderedIds.map((id) => {
    const left = leftMetrics.get(id);
    const right = rightMetrics.get(id);
    const leftValue = isAvailable(left?.value) ? left.value : 'Data unavailable';
    const rightValue = isAvailable(right?.value) ? right.value : 'Data unavailable';

    return {
      id,
      label: left?.label || right?.label || id,
      leftValue,
      rightValue,
      comparable: leftValue !== 'Data unavailable' && rightValue !== 'Data unavailable',
    };
  });
}
