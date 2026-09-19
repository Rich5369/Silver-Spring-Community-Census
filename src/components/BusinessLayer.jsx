import BusinessMarker from './BusinessMarker';

function BusinessLayer({ businesses = [], evidenceSources = [] }) {
  return businesses.map((business) => (
    <BusinessMarker
      key={business.id}
      business={business}
      sources={evidenceSources.filter((source) => business.sourceIds?.includes(source.id))}
    />
  ));
}

export default BusinessLayer;
