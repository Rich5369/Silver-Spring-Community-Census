const finiteNumber = (value) => {
  if (value === null || value === undefined || value === '') return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
};

const formatInteger = (value) => (
  new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(value)
);

const formatCurrency = (value) => (
  new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(value)
);

const isPosition = (position) => (
  Array.isArray(position)
  && position.length >= 2
  && Number.isFinite(Number(position[0]))
  && Number.isFinite(Number(position[1]))
);

const isLinearRing = (ring) => (
  Array.isArray(ring) && ring.length >= 4 && ring.every(isPosition)
);

const isPolygonCoordinates = (coordinates) => (
  Array.isArray(coordinates) && coordinates.length > 0 && coordinates.every(isLinearRing)
);

function hasValidPolygonGeometry(feature) {
  const geometry = feature?.geometry;
  if (feature?.type !== 'Feature' || !geometry) return false;
  if (geometry.type === 'Polygon') return isPolygonCoordinates(geometry.coordinates);
  if (geometry.type === 'MultiPolygon') {
    return Array.isArray(geometry.coordinates)
      && geometry.coordinates.length > 0
      && geometry.coordinates.every(isPolygonCoordinates);
  }
  return false;
}

export function sanitizeGeoJsonFeatureCollection(data) {
  if (data?.type !== 'FeatureCollection' || !Array.isArray(data.features)) return null;
  const features = data.features.filter(hasValidPolygonGeometry);
  if (features.length === 0) return null;
  return features.length === data.features.length ? data : { ...data, features };
}

function normalizeFeatureSources(sourceValue, areaId) {
  const records = Array.isArray(sourceValue) ? sourceValue : sourceValue ? [sourceValue] : [];

  return records.map((source, index) => {
    const record = typeof source === 'string' ? { organization: source } : source;

    return {
      id: String(record?.id || `${areaId}-source-${index + 1}`),
      organization: String(record?.organization || ''),
      dataset: String(record?.dataset || ''),
      year: String(record?.year || record?.dataset_year || ''),
      geography: String(record?.geography || ''),
      table: String(record?.table || record?.field || record?.source_variable || ''),
      url: String(record?.url || record?.source_url || ''),
    };
  });
}

function formatPercent(value) {
  return `${new Intl.NumberFormat('en-US', { maximumFractionDigits: 1 }).format(value)}%`;
}

const backendMetricDefinitions = [
  { key: 'total_population', label: 'Population', format: formatInteger },
  { key: 'median_household_income', label: 'Median household income', format: formatCurrency },
  { key: 'median_age', label: 'Median age', format: (value) => `${formatInteger(value)} years` },
  { key: 'renter_share', label: 'Renter households', format: formatPercent },
  { key: 'multilingual_household_share', label: 'Multilingual households', format: formatPercent },
  { key: 'commute_active_share', label: 'Walk or bike commute', format: formatPercent },
];

export function getGeoJsonAreaId(feature) {
  return String(
    feature?.id
      ?? feature?.properties?.geoid
      ?? feature?.properties?.areaName
      ?? 'unnamed-area',
  );
}

export function normalizeGeoJsonArea(feature) {
  const properties = feature?.properties ?? {};
  const areaId = getGeoJsonAreaId(feature);
  const backendMetrics = properties.metrics && typeof properties.metrics === 'object'
    ? properties.metrics
    : null;
  const legacySources = normalizeFeatureSources(properties.sources ?? properties.source, areaId);
  const metricSources = backendMetrics
    ? backendMetricDefinitions.flatMap(({ key }) => {
      const evidence = backendMetrics[key]?.evidence;
      return evidence
        ? normalizeFeatureSources({ ...evidence, id: `${areaId}-${key}`, geography: properties.name }, areaId)
        : [];
    })
    : [];
  const boundarySources = normalizeFeatureSources(properties.boundary_source, `${areaId}-boundary`);
  const sources = [...legacySources, ...metricSources, ...boundarySources].filter(
    (source, index, records) => records.findIndex((record) => record.id === source.id) === index,
  );
  const legacySourceIds = legacySources.map((source) => source.id);
  const stats = backendMetrics
    ? backendMetricDefinitions.map(({ key, label, format }) => {
      const metric = backendMetrics[key];
      const value = finiteNumber(metric?.value);
      const sourceId = metric?.evidence ? `${areaId}-${key}` : null;
      return {
        id: key,
        label,
        value: value === null ? 'Data unavailable' : format(value),
        note: metric?.evidence?.dataset_year
          ? `${metric.evidence.dataset} (${metric.evidence.dataset_year})`
          : 'Source metadata not provided',
        sourceIds: sourceId ? [sourceId] : [],
      };
    })
    : [
      {
        id: 'population',
        label: 'Population',
        value: finiteNumber(properties.population) === null
          ? 'Data unavailable'
          : formatInteger(finiteNumber(properties.population)),
        note: 'GeoJSON feature property',
        sourceIds: legacySourceIds,
      },
      {
        id: 'income',
        label: 'Median household income',
        value: finiteNumber(properties.medianIncome) === null
          ? 'Data unavailable'
          : formatCurrency(finiteNumber(properties.medianIncome)),
        note: 'GeoJSON feature property',
        sourceIds: legacySourceIds,
      },
    ];

  return {
    areaId,
    areaName: String(properties.areaName || properties.name || 'Unnamed geographic area'),
    summary: backendMetrics
      ? 'Selected Census tract in the Silver Spring study area.'
      : 'Selected geographic area from the connected GeoJSON layer.',
    dataStatus: metricSources.length > 0
      ? 'Connected Census data with source evidence'
      : sources.length > 0
        ? 'Connected GeoJSON data'
      : 'Source metadata not provided',
    stats,
    sources,
  };
}
