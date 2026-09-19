import BusinessMarker from './BusinessMarker';

function BusinessLayer({ businesses = [] }) {
  return businesses.map((business) => (
    <BusinessMarker key={business.id} business={business} />
  ));
}

export default BusinessLayer;
