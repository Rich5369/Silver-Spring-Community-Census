import { useState } from 'react';
import CommunityMap from './CommunityMap';
import { fentonVillage, silverSpringMapView } from '../data/mapData';

function MapPanel() {
  const [resetKey, setResetKey] = useState(0);

  return (
    <section className="map-panel" aria-label="Community map">
      <div className="map-toolbar">
        <div>
          <p className="eyebrow">Map view</p>
          <h2>Fenton Village</h2>
        </div>
        <button
          className="secondary-button"
          type="button"
          onClick={() => setResetKey((key) => key + 1)}
        >
          Reset view
        </button>
      </div>

      <CommunityMap
        center={silverSpringMapView.center}
        zoom={silverSpringMapView.zoom}
        locations={[fentonVillage]}
        resetKey={resetKey}
      />
    </section>
  );
}

export default MapPanel;
