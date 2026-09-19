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
  onAreaSelect,
}) {
  return (
    <>
      {visibility.businesses && (
        <BusinessLayer businesses={businesses} evidenceSources={evidenceSources} />
      )}
      {visibility.community && communityGeoJson && (
        <CensusAreaLayer
          data={communityGeoJson}
          selectedAreaId={selectedAreaId}
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
