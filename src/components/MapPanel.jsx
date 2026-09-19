import { useState } from 'react';
import CommunityMap from './CommunityMap';
import { fentonVillage, silverSpringMapView } from '../data/mapData';

function MapPanel({
  areaName = 'Fenton Village',
  businesses = [],
  businessLayerAvailable = false,
  evidenceSources = [],
  communityGeoJson = null,
  selectedAreaId = null,
  onAreaSelect,
  onDefaultAreaSelect,
  onExploreFenton,
  exploreKey = 0,
  hasActiveQuery = false,
}) {
  const [resetKey, setResetKey] = useState(0);

  return (
    <section className="map-panel" aria-label="Community map">
      <div className="map-toolbar">
        <div>
          <p className="eyebrow">Map view</p>
          <h2>{areaName}</h2>
        </div>
        <div className="map-toolbar-actions">
          <button className="primary-button" type="button" onClick={onExploreFenton}>
            Explore Fenton Village
          </button>
          <button
            className="secondary-button"
            type="button"
            onClick={() => setResetKey((key) => key + 1)}
          >
            Reset view
          </button>
        </div>
      </div>

      <CommunityMap
        center={silverSpringMapView.center}
        zoom={silverSpringMapView.zoom}
        focusCenter={fentonVillage.position}
        focusZoom={16}
        locations={[fentonVillage]}
        businesses={businesses}
        businessLayerAvailable={businessLayerAvailable}
        evidenceSources={evidenceSources}
        communityGeoJson={communityGeoJson}
        selectedAreaId={selectedAreaId}
        onAreaSelect={onAreaSelect}
        onDefaultAreaSelect={onDefaultAreaSelect}
        showEmptyResults={businesses.length === 0}
        emptyResultsMessage={hasActiveQuery
          ? 'Try another category or clear the search.'
          : 'No business records are available for this area.'}
        resetKey={resetKey}
        exploreKey={exploreKey}
      />
    </section>
  );
}

export default MapPanel;
