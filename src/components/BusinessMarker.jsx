import { CircleMarker, Popup } from 'react-leaflet';

function BusinessMarker({ business }) {
  return (
    <CircleMarker
      center={[business.latitude, business.longitude]}
      radius={7}
      pathOptions={{ color: '#ffffff', fillColor: '#286b4c', fillOpacity: 0.95, weight: 2 }}
    >
      <Popup>
        <article className="business-popup">
          <span className="mock-data-label">Mock business</span>
          <strong>{business.name}</strong>
          <dl>
            <div>
              <dt>Category</dt>
              <dd>{business.category}</dd>
            </div>
            <div>
              <dt>Address</dt>
              <dd>{business.address}</dd>
            </div>
            <div>
              <dt>Source</dt>
              <dd>{business.source}</dd>
            </div>
          </dl>
        </article>
      </Popup>
    </CircleMarker>
  );
}

export default BusinessMarker;
