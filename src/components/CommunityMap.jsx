import { useEffect } from 'react';
import { CircleMarker, MapContainer, Popup, TileLayer, useMap } from 'react-leaflet';

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

function CommunityMap({ center, zoom, locations = [], resetKey = 0 }) {
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
        <MapController center={center} zoom={zoom} resetKey={resetKey} />
      </MapContainer>
    </div>
  );
}

export default CommunityMap;
