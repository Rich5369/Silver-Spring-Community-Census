import { useMemo } from 'react';
import BusinessMarker from './BusinessMarker';

function BusinessLayer({
  businesses = [],
  evidenceSources = [],
  businessFocus,
  selectedBusinessId = null,
  onBusinessSelect,
  isVisible = true,
}) {
  // Each marker used to scan the whole evidence list for its own sources, so
  // the layer cost businesses x sources on every render and handed each marker
  // a freshly built array, which defeated memoisation. One indexed pass here
  // gives every marker a stable array instead.
  const sourcesByBusinessId = useMemo(() => {
    const byId = new Map(evidenceSources.map((source) => [source.id, source]));
    return new Map(businesses.map((business) => [
      business.id,
      (business.sourceIds ?? []).flatMap((id) => (byId.has(id) ? [byId.get(id)] : [])),
    ]));
  }, [businesses, evidenceSources]);

  return businesses.map((business) => (
    <BusinessMarker
      key={business.id}
      business={business}
      focusRequest={businessFocus?.business.id === business.id ? businessFocus : null}
      isSelected={selectedBusinessId === business.id}
      onSelect={onBusinessSelect}
      isVisible={isVisible}
      sources={sourcesByBusinessId.get(business.id)}
    />
  ));
}

export default BusinessLayer;
