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

const highlightedStyle = {
  color: '#286b4c',
  fillColor: '#55a276',
  fillOpacity: 0.38,
  weight: 3,
};

function CensusAreaLayer({ data, selectedAreaId = null, highlightedAreaIds = [], onAreaSelect }) {
  const safeData = sanitizeGeoJsonFeatureCollection(data);
  if (!safeData) return null;

  const highlighted = new Set(highlightedAreaIds);
  const styleFeature = (feature) => {
    const id = getGeoJsonAreaId(feature);
    if (id === selectedAreaId) return selectedStyle;
    return highlighted.has(id) ? highlightedStyle : defaultStyle;
  };

  const bindFeature = (feature, layer) => {
    const selectArea = () => onAreaSelect?.(normalizeGeoJsonArea(feature));
    const makeKeyboardAccessible = () => {
      const element = layer.getElement?.();
      if (!element) return;

      const area = normalizeGeoJsonArea(feature);
      element.setAttribute('tabindex', '0');
      element.setAttribute('role', 'button');
      element.setAttribute('aria-label', `Select ${area.areaName || 'community area'}`);
      element.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          selectArea();
        }
      }, { once: false });
    };

    layer.on({
      click: selectArea,
      add: makeKeyboardAccessible,
    });
  };

  return <GeoJSON data={safeData} style={styleFeature} onEachFeature={bindFeature} />;
}

export default CensusAreaLayer;
