const layerOptions = [
  { id: 'businesses', label: 'Businesses' },
  { id: 'community', label: 'Community / Demographics' },
  { id: 'transit', label: 'Transit' },
];

function MapLayersControl({ visibility, availability, onChange }) {
  return (
    <details className="map-layers-control" open>
      <summary>Map Layers</summary>
      <div className="map-layer-options">
        {layerOptions.map((layer) => {
          const isAvailable = Boolean(availability[layer.id]);

          return (
            <label className={isAvailable ? 'map-layer-option' : 'map-layer-option unavailable'} key={layer.id}>
              <input
                type="checkbox"
                checked={isAvailable && Boolean(visibility[layer.id])}
                disabled={!isAvailable}
                onChange={(event) => onChange(layer.id, event.target.checked)}
              />
              <span>
                <strong>{layer.label}</strong>
                {!isAvailable && <small>Data not connected yet</small>}
              </span>
            </label>
          );
        })}
      </div>
    </details>
  );
}

export default MapLayersControl;
