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
      year: String(record?.year || ''),
      geography: String(record?.geography || ''),
      table: String(record?.table || record?.field || ''),
      url: String(record?.url || ''),
    };
  });
}

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
  const sources = normalizeFeatureSources(properties.sources ?? properties.source, areaId);
  const sourceIds = sources.map((source) => source.id);
  const population = finiteNumber(properties.population);
  const medianIncome = finiteNumber(properties.medianIncome);
  const stats = [
    {
      id: 'population',
      label: 'Population',
      value: population === null ? 'Data unavailable' : formatInteger(population),
      note: population === null ? 'GeoJSON property not provided' : 'GeoJSON feature property',
      sourceIds,
    },
    {
      id: 'income',
      label: 'Median household income',
      value: medianIncome === null ? 'Data unavailable' : formatCurrency(medianIncome),
      note: medianIncome === null ? 'GeoJSON property not provided' : 'GeoJSON feature property',
      sourceIds,
    },
  ];

  return {
    areaId,
    areaName: String(properties.areaName || 'Unnamed geographic area'),
    summary: 'Selected geographic area from the connected GeoJSON layer.',
    dataStatus: sources.length > 0
      ? 'Connected GeoJSON data'
      : 'Source metadata not provided',
    stats,
    sources,
  };
}
