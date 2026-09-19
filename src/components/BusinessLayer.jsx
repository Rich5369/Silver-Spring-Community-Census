import BusinessMarker from './BusinessMarker';

function BusinessLayer({
  businesses = [],
  evidenceSources = [],
  businessFocus,
  selectedBusinessId = null,
  onBusinessSelect,
  isVisible = true,
}) {
  return businesses.map((business) => (
    <BusinessMarker
      key={business.id}
      business={business}
      focusRequest={businessFocus?.business.id === business.id ? businessFocus : null}
      isSelected={selectedBusinessId === business.id}
      onSelect={onBusinessSelect}
      isVisible={isVisible}
      sources={evidenceSources.filter((source) => business.sourceIds?.includes(source.id))}
    />
  ));
}

export default BusinessLayer;
