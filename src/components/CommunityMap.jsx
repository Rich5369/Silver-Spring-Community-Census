import { useEffect, useState } from 'react';
import { CircleMarker, MapContainer, Popup, TileLayer, useMap } from 'react-leaflet';
import MapDataLayers from './MapDataLayers';
import MapLayersControl from './MapLayersControl';
import { sanitizeGeoJsonFeatureCollection } from '../services/geoJsonAdapter';

function MapController({ center, zoom, focusCenter, focusZoom, exploreKey, resetKey }) {
  const map = useMap();

  useEffect(() => {
    map.setView(center, zoom);
  }, [center, map, resetKey, zoom]);

  useEffect(() => {
    if (exploreKey > 0) {
      map.flyTo(focusCenter, focusZoom, { animate: true, duration: 1.1 });
    }
  }, [exploreKey, focusCenter, focusZoom, map]);

  useEffect(() => {
    const container = map.getContainer();
    const observer = new ResizeObserver(() => map.invalidateSize());

    observer.observe(container);
    map.invalidateSize();

    return () => observer.disconnect();
  }, [map]);

  return null;
}

function hasGeoJsonData(data) {
  if (!data || typeof data !== 'object') return false;
  if (data.type === 'FeatureCollection') return Array.isArray(data.features) && data.features.length > 0;
  if (data.type === 'Feature') return Boolean(data.geometry);
  return Boolean(data.type && data.coordinates);
}

function CommunityMap({
  center,
  zoom,
  focusCenter = center,
  focusZoom = zoom,
  locations = [],
  businesses = [],
  businessLayerAvailable = false,
  evidenceSources = [],
  communityGeoJson = null,
  transitGeoJson = null,
  selectedAreaId = null,
  onAreaSelect,
  onDefaultAreaSelect,
  showEmptyResults = false,
  emptyResultsMessage = 'No business records are available.',
  resetKey = 0,
  exploreKey = 0,
}) {
  const [layerVisibility, setLayerVisibility] = useState({
    businesses: true,
    community: false,
    transit: false,
  });
  const safeCommunityGeoJson = sanitizeGeoJsonFeatureCollection(communityGeoJson);
  const layerAvailability = {
    businesses: businessLayerAvailable || businesses.length > 0,
    community: Boolean(safeCommunityGeoJson),
    transit: hasGeoJsonData(transitGeoJson),
  };
  const isDemoLayer = businesses.length > 0 && businesses.every((business) => (
    /demo|mock|illustrative/i.test(business.source || '')
  ));
  const updateLayerVisibility = (layerId, isVisible) => {
    setLayerVisibility((current) => ({ ...current, [layerId]: isVisible }));
  };

  useEffect(() => {
    if (exploreKey > 0) {
      setLayerVisibility((current) => ({ ...current, businesses: true }));
    }
  }, [exploreKey]);
  const selectArea = (area) => {
    onAreaSelect?.(area);
  };

  return (
    <div className="map-canvas">
      <MapContainer
        center={center}
        zoom={zoom}
        zoomControl
        scrollWheelZoom
        className="leaflet-map"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {locations.map((location) => (
          <CircleMarker
            key={location.id}
            center={location.position}
            radius={10}
            pathOptions={{ color: '#ffffff', fillColor: '#c95832', fillOpacity: 1, weight: 3 }}
            eventHandlers={{ click: () => onDefaultAreaSelect?.() }}
          >
            <Popup>
              <strong>{location.name}</strong>
              <p>{location.description}</p>
            </Popup>
          </CircleMarker>
        ))}
        <MapDataLayers
          visibility={layerVisibility}
          businesses={businesses}
          evidenceSources={evidenceSources}
          communityGeoJson={safeCommunityGeoJson}
          transitGeoJson={transitGeoJson}
          selectedAreaId={selectedAreaId}
          onAreaSelect={selectArea}
        />
        <MapController
          center={center}
          zoom={zoom}
          focusCenter={focusCenter}
          focusZoom={focusZoom}
          exploreKey={exploreKey}
          resetKey={resetKey}
        />
      </MapContainer>
      <MapLayersControl
        visibility={layerVisibility}
        availability={layerAvailability}
        onChange={updateLayerVisibility}
      />
      {layerVisibility.businesses && businesses.length > 0 && (
        <div className="mock-layer-notice" role="note">
          {isDemoLayer
            ? `Demo layer: ${businesses.length} mock businesses — not verified data`
            : `${businesses.length} businesses shown`}
        </div>
      )}
      {layerVisibility.businesses && showEmptyResults && (
        <div className="map-empty-results" role="status">
          <strong>No businesses found</strong>
          <span>{emptyResultsMessage}</span>
        </div>
      )}
    </div>
  );
}

export default CommunityMap;
