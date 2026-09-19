import { GeoJSON } from 'react-leaflet';
import BusinessLayer from './BusinessLayer';
import CensusAreaLayer from './CensusAreaLayer';

function MapDataLayers({
  visibility,
  businesses = [],
  evidenceSources = [],
  communityGeoJson = null,
  transitGeoJson = null,
  selectedAreaId = null,
  highlightedAreaIds = [],
  selectedBusinessId = null,
  onBusinessSelect,
  isVisible = true,
  onAreaSelect,
  businessFocus,
}) {
  return (
    <>
      {visibility.businesses && (
        <BusinessLayer
          businesses={businesses}
          evidenceSources={evidenceSources}
          businessFocus={businessFocus}
          selectedBusinessId={selectedBusinessId}
          onBusinessSelect={onBusinessSelect}
          isVisible={isVisible}
        />
      )}
      {visibility.community && communityGeoJson && (
        <CensusAreaLayer
          data={communityGeoJson}
          selectedAreaId={selectedAreaId}
          highlightedAreaIds={highlightedAreaIds}
          onAreaSelect={onAreaSelect}
        />
      )}
      {visibility.transit && transitGeoJson && (
        <GeoJSON data={transitGeoJson} />
      )}
    </>
  );
}

export default MapDataLayers;
