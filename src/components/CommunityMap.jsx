import { useEffect } from 'react';
import { CircleMarker, MapContainer, Popup, TileLayer, useMap } from 'react-leaflet';
import BusinessLayer from './BusinessLayer';

function MapController({ center, zoom, resetKey }) {
  const map = useMap();

  useEffect(() => {
    map.setView(center, zoom);
  }, [center, map, resetKey, zoom]);

  useEffect(() => {
    const container = map.getContainer();
    const observer = new ResizeObserver(() => map.invalidateSize());

    observer.observe(container);
    map.invalidateSize();

    return () => observer.disconnect();
  }, [map]);

  return null;
}

function CommunityMap({
  center,
  zoom,
  locations = [],
  businesses = [],
  evidenceSources = [],
  showEmptyResults = false,
  emptyResultsMessage = 'No business records are available.',
  resetKey = 0,
}) {
  const isDemoLayer = businesses.length > 0 && businesses.every((business) => (
    /demo|mock|illustrative/i.test(business.source || '')
  ));

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
          >
            <Popup>
              <strong>{location.name}</strong>
              <p>{location.description}</p>
            </Popup>
          </CircleMarker>
        ))}
        <BusinessLayer businesses={businesses} evidenceSources={evidenceSources} />
        <MapController center={center} zoom={zoom} resetKey={resetKey} />
      </MapContainer>
      {businesses.length > 0 && (
        <div className="mock-layer-notice" role="note">
          {isDemoLayer
            ? `Demo layer: ${businesses.length} mock businesses — not verified data`
            : `${businesses.length} businesses shown`}
        </div>
      )}
      {showEmptyResults && (
        <div className="map-empty-results" role="status">
          <strong>No businesses found</strong>
          <span>{emptyResultsMessage}</span>
        </div>
      )}
    </div>
  );
}

export default CommunityMap;
