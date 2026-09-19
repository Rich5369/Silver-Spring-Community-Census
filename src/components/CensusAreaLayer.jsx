import { GeoJSON } from 'react-leaflet';
import {
  getGeoJsonAreaId,
  normalizeGeoJsonArea,
  sanitizeGeoJsonFeatureCollection,
} from '../services/geoJsonAdapter';

const defaultStyle = {
  color: '#397254',
  fillColor: '#78a98b',
  fillOpacity: 0.18,
  weight: 2,
};

const selectedStyle = {
  color: '#b44f2c',
  fillColor: '#d9835f',
  fillOpacity: 0.32,
  weight: 4,
};

function CensusAreaLayer({ data, selectedAreaId = null, onAreaSelect }) {
  const safeData = sanitizeGeoJsonFeatureCollection(data);
  if (!safeData) return null;

  const styleFeature = (feature) => (
    getGeoJsonAreaId(feature) === selectedAreaId ? selectedStyle : defaultStyle
  );

  const bindFeature = (feature, layer) => {
    layer.on({
      click: () => onAreaSelect?.(normalizeGeoJsonArea(feature)),
    });
  };

  return <GeoJSON data={safeData} style={styleFeature} onEachFeature={bindFeature} />;
}

export default CensusAreaLayer;
