import { useEffect, useRef } from 'react';
import { CircleMarker, Popup, useMap } from 'react-leaflet';
import EvidenceDetails from './EvidenceDetails';
import BusinessStatus from './BusinessStatus';

function BusinessMarker({ business, sources = [], focusRequest, isSelected = false, onSelect, isVisible = true }) {
  const markerRef = useRef(null);
  const popupContentRef = useRef(null);
  const map = useMap();
  const focusPopup = () => requestAnimationFrame(() => popupContentRef.current?.focus({ preventScroll: true }));
  useEffect(() => {
    if (!isSelected) return undefined;
    markerRef.current?.bringToFront();
    // Leaflet reattaches popup content while React updates the selected marker.
    // Focus after that content update so it is not lost when the node moves.
    const timer = setTimeout(() => popupContentRef.current?.focus({ preventScroll: true }), 0);
    return () => clearTimeout(timer);
  }, [isSelected]);
  const businessSources = sources.length > 0
    ? sources
    : [{
      organization: business.source,
      dataset: business.dataset || 'Business record',
      year: '',
      geography: 'Fenton Village',
      table: '',
      url: business.sourceUrl || '',
    }];
  useEffect(() => {
    if (!focusRequest) return undefined;
    const frame = requestAnimationFrame(() => {
      map.invalidateSize();
      map.setView([business.latitude, business.longitude], 17, { animate: false });
      markerRef.current?.openPopup();
      focusPopup();
    });
    return () => cancelAnimationFrame(frame);
  }, [focusRequest, map, business.latitude, business.longitude]);

  // Selection is owned by the panel, so clearing it elsewhere must close this popup too.
  useEffect(() => {
    if (!isSelected) markerRef.current?.closePopup();
  }, [isSelected]);

  useEffect(() => {
    const marker = markerRef.current;
    const element = marker?.getElement?.();
    if (!element) return undefined;

    element.setAttribute('tabindex', '0');
    element.setAttribute('role', 'button');
    element.setAttribute(
      'aria-label',
      `${business.name}, ${business.category}${isSelected ? ', selected' : ''}. Open business details.`,
    );
    element.setAttribute('aria-expanded', String(isSelected));
    const openWithKeyboard = (event) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        marker.openPopup();
        focusPopup();
      }
    };
    element.addEventListener('keydown', openWithKeyboard);

    return () => element.removeEventListener('keydown', openWithKeyboard);
  }, [business.name, business.category, isSelected]);

  return (
    <CircleMarker
      ref={markerRef}
      center={[business.latitude, business.longitude]}
      radius={isSelected ? 11 : 7}
      pane="businessMarkersPane"
      bubblingMouseEvents={false}
      pathOptions={{
        color: isSelected ? '#173f31' : '#ffffff',
        fillColor: '#286b4c',
        fillOpacity: 0.95,
        weight: isSelected ? 4 : 2,
      }}
      eventHandlers={{
        click: (event) => {
          event.originalEvent?.stopPropagation();
        },
        popupopen: () => { onSelect?.(business.id); markerRef.current?.bringToFront(); },
        // Hiding the map for the List view closes popups; that must not drop the selection.
        popupclose: () => { if (isVisible && isSelected) onSelect?.(null); },
      }}
    >
      <Popup>
        <article
          className="business-popup"
          ref={popupContentRef}
          tabIndex={-1}
          aria-label={`${business.name} details`}
          onKeyDown={(event) => {
            if (event.key === 'Escape') {
              markerRef.current?.closePopup();
              markerRef.current?.getElement()?.focus();
            }
          }}
        >
          <h3>{business.name}</h3>
          <dl>
            <div>
              <dt>Category</dt>
              <dd>{business.category}</dd>
            </div>
            <div>
              <dt>Address</dt>
              <dd>{business.address || 'Address not provided'}</dd>
            </div>
            <div>
              <dt>Data source</dt>
              <dd><BusinessStatus business={business} sources={businessSources} /></dd>
            </div>
          </dl>
          <EvidenceDetails sources={businessSources} label="Evidence" />
        </article>
      </Popup>
    </CircleMarker>
  );
}

export default BusinessMarker;
