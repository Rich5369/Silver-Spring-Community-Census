import { useEffect, useRef, useState } from 'react';
import { CircleMarker, MapContainer, Popup, TileLayer, useMap } from 'react-leaflet';
import MapDataLayers from './MapDataLayers';
import MapLayersControl from './MapLayersControl';
import { sanitizeGeoJsonFeatureCollection } from '../services/geoJsonAdapter';
import { areAllDemoBusinesses } from '../services/provenance';

function MapController({ center, zoom, focusCenter, focusZoom, exploreKey, resetKey, isVisible }) {
  const map = useMap();
  useEffect(() => {
    if (!isVisible) { map.stop(); map.closePopup(); }
    else map.invalidateSize();
  }, [isVisible, map]);

  useEffect(() => {
    map.setView(center, zoom);
  }, [center, map, resetKey, zoom]);

  useEffect(() => {
    if (exploreKey > 0) {
      const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
      map.flyTo(focusCenter, focusZoom, {
        animate: !reduceMotion,
        duration: reduceMotion ? 0 : 1.1,
      });
    }
  }, [exploreKey, focusCenter, focusZoom, map]);

  useEffect(() => {
    const container = map.getContainer();
    const observer = new ResizeObserver(() => {
      if (container.clientWidth && container.clientHeight) map.invalidateSize();
    });

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

function LocationMarker({ location, onSelect }) {
  const markerRef = useRef(null);

  useEffect(() => {
    const marker = markerRef.current;
    const element = marker?.getElement?.();
    if (!element) return undefined;

    element.setAttribute('tabindex', '0');
    element.setAttribute('role', 'button');
    element.setAttribute('aria-label', `${location.name} — focus area for this project. Select for details.`);
    const openWithKeyboard = (event) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        onSelect?.();
        marker.openPopup();
      }
    };
    element.addEventListener('keydown', openWithKeyboard);

    return () => element.removeEventListener('keydown', openWithKeyboard);
  }, [location.name, onSelect]);

  // Business markers render into the default overlay pane. Drawing the landmark
  // into the higher marker pane keeps it visible no matter how many businesses
  // surround it - otherwise 207 of them simply paint over it.
  return (
    <CircleMarker
      ref={markerRef}
      center={location.position}
      radius={10}
      pane="markerPane"
      pathOptions={{ color: '#ffffff', fillColor: '#c95832', fillOpacity: 1, weight: 3 }}
      eventHandlers={{ click: onSelect }}
    >
      <Popup>
        <strong>{location.name}</strong>
        <p>{location.description}</p>
      </Popup>
    </CircleMarker>
  );
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
  selectedBusinessId = null,
  onBusinessSelect,
  onAreaSelect,
  onDefaultAreaSelect,
  showEmptyResults = false,
  emptyResultsMessage = 'No business records are available.',
  resetKey = 0,
  exploreKey = 0,
  businessFocus = null,
  isVisible = true,
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
  const isDemoLayer = areAllDemoBusinesses(businesses);
  const updateLayerVisibility = (layerId, isVisible) => {
    setLayerVisibility((current) => ({ ...current, [layerId]: isVisible }));
  };

  useEffect(() => {
    if (exploreKey > 0) {
      setLayerVisibility((current) => ({ ...current, businesses: true }));
    }
  }, [exploreKey]);
  useEffect(() => {
    if (businessFocus) setLayerVisibility((current) => ({ ...current, businesses: true }));
  }, [businessFocus]);
  const selectArea = (area) => {
    onAreaSelect?.(area);
  };

  return (
    <div
      className="map-canvas"
      role="region"
      aria-label="Interactive community map of Silver Spring, Maryland"
      aria-describedby="map-accessibility-description"
    >
      <p className="visually-hidden" id="map-accessibility-description">
        Markers can be reached with the Tab key and opened with Enter or Space. If the map is
        hard to navigate, switch to the List view to read every matching business as text, then
        use View on map to move the map to it and open its details.
      </p>
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
          <LocationMarker
            key={location.id}
            location={location}
            onSelect={onDefaultAreaSelect}
          />
        ))}
        <MapDataLayers
          businessFocus={businessFocus}
          visibility={layerVisibility}
          businesses={businesses}
          evidenceSources={evidenceSources}
          communityGeoJson={safeCommunityGeoJson}
          transitGeoJson={transitGeoJson}
          selectedAreaId={selectedAreaId}
          selectedBusinessId={selectedBusinessId}
          onBusinessSelect={onBusinessSelect}
          isVisible={isVisible}
          onAreaSelect={selectArea}
        />
        <MapController
          isVisible={isVisible}
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
      <section className="map-legend" aria-labelledby="map-legend-title">
        <h3 id="map-legend-title">What the markers mean</h3>
        <ul>
          <li>
            <i className="legend-focus" aria-hidden="true" />
            <span><strong>Large orange dot</strong> — Fenton Village, the focus area for this project</span>
          </li>
          {layerVisibility.businesses && businesses.length > 0 && (
            <>
              <li>
                <i className="legend-business" aria-hidden="true" />
                <span><strong>Small green dot</strong> — a business. Select it for name, category and address</span>
              </li>
              <li>
                <i className="legend-selected" aria-hidden="true" />
                <span><strong>Green dot with a dark ring</strong> — the business you selected</span>
              </li>
            </>
          )}
          {layerVisibility.community && layerAvailability.community && (
            <li>
              <i className="legend-area" aria-hidden="true" />
              <span><strong>Shaded outline</strong> — census tract boundary</span>
            </li>
          )}
        </ul>
      </section>
    </div>
  );
}

export default CommunityMap;
