import { useEffect, useState } from 'react';
import CommunityMap from './CommunityMap';
import BusinessList from './BusinessList';
import { describeResultCount } from '../services/businessQuery';
import { fentonVillage, silverSpringMapView } from '../data/mapData';

const views = [
  { id: 'map', label: 'Map' },
  { id: 'list', label: 'List' },
];

function MapPanel({
  areaName = 'Fenton Village',
  businesses = [],
  totalBusinessCount = 0,
  businessLayerAvailable = false,
  evidenceSources = [],
  communityGeoJson = null,
  selectedAreaId = null,
  highlightedAreaIds = [],
  onAreaSelect,
  onDefaultAreaSelect,
  onExploreFenton,
  exploreKey = 0,
  hasActiveQuery = false,
}) {
  const [resetKey, setResetKey] = useState(0);
  const [view, setView] = useState('map');
  const [businessFocus, setBusinessFocus] = useState(null);
  const [selectedBusinessId, setSelectedBusinessId] = useState(null);
  const emptyMessage = hasActiveQuery
    ? 'Try another category or clear the search.'
    : 'No business records are available for this area.';
  const selectedBusiness = businesses.find((business) => business.id === selectedBusinessId) ?? null;

  // The map and the list share one filtered result set, so a business that a filter
  // removes must also stop being the selected business.
  useEffect(() => {
    if (selectedBusinessId === null) return;
    if (!businesses.some((business) => business.id === selectedBusinessId)) {
      setSelectedBusinessId(null);
      setBusinessFocus(null);
    }
  }, [businesses, selectedBusinessId]);

  const clearSelection = () => {
    setSelectedBusinessId(null);
    setBusinessFocus(null);
  };

  const viewOnMap = (business) => {
    setView('map');
    setSelectedBusinessId(business.id);
    setBusinessFocus({ business });
  };

  return (
    <section className="map-panel" aria-label="Community map">
      <div className="map-toolbar">
        <div>
          <p className="eyebrow">Explore the area</p>
          <h2>{areaName}</h2>
        </div>
        <div className="map-toolbar-actions">
          <button
            className="primary-button"
            type="button"
            onClick={() => { setView('map'); clearSelection(); onExploreFenton(); }}
          >
            Explore Fenton Village
          </button>
          <button
            className="secondary-button"
            type="button"
            onClick={() => { setView('map'); clearSelection(); setResetKey((key) => key + 1); }}
          >
            Reset view
          </button>
        </div>
      </div>
      <div className="results-toolbar">
        <div className="view-toggle" role="group" aria-label="Business results view">
          {views.map((mode) => (
            <button
              key={mode.id}
              type="button"
              aria-pressed={view === mode.id}
              aria-controls={`business-${mode.id}-view`}
              onClick={() => setView(mode.id)}
            >
              {mode.label}
            </button>
          ))}
        </div>
        <p className="result-summary">{describeResultCount(businesses.length, totalBusinessCount)}</p>
      </div>
      {selectedBusiness && (
        <div className="selected-business-bar">
          <p>
            <span className="selected-flag">Selected</span>
            <strong>{selectedBusiness.name}</strong>
            <span className="selected-category">{selectedBusiness.category}</span>
          </p>
          <div className="selected-business-actions">
            {view === 'list' && (
              <button
                className="secondary-button"
                type="button"
                onClick={() => viewOnMap(selectedBusiness)}
              >
                View on map
              </button>
            )}
            <button
              className="secondary-button"
              type="button"
              onClick={clearSelection}
            >
              Clear selection
            </button>
          </div>
        </div>
      )}
      <div id="business-map-view" className="business-map-view" hidden={view !== 'map'}>
        <CommunityMap
          isVisible={view === 'map'}
          businessFocus={businessFocus}
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
          highlightedAreaIds={highlightedAreaIds}
          selectedBusinessId={selectedBusinessId}
          onBusinessSelect={setSelectedBusinessId}
          onAreaSelect={onAreaSelect}
          onDefaultAreaSelect={onDefaultAreaSelect}
          showEmptyResults={businesses.length === 0}
          emptyResultsMessage={emptyMessage}
          resetKey={resetKey}
          exploreKey={exploreKey}
        />
      </div>
      <div id="business-list-view" className="business-list-panel" hidden={view !== 'list'}>
        <BusinessList
          businesses={businesses}
          evidenceSources={evidenceSources}
          selectedBusinessId={selectedBusinessId}
          onViewOnMap={viewOnMap}
          emptyMessage={emptyMessage}
        />
      </div>
    </section>
  );
}

export default MapPanel;
