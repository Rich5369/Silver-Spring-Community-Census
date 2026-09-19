import { CircleMarker, Popup } from 'react-leaflet';
import EvidenceDetails from './EvidenceDetails';

function BusinessMarker({ business, sources = [] }) {
  const businessSources = sources.length > 0
    ? sources
    : [{
      organization: business.source,
      dataset: 'Business record',
      year: '',
      geography: 'Fenton Village',
      table: '',
      url: '',
    }];
  const isDemo = /demo|mock|illustrative/i.test(
    `${business.source || ''} ${businessSources.map((source) => `${source.organization} ${source.dataset}`).join(' ')}`,
  );

  return (
    <CircleMarker
      center={[business.latitude, business.longitude]}
      radius={7}
      pathOptions={{ color: '#ffffff', fillColor: '#286b4c', fillOpacity: 0.95, weight: 2 }}
    >
      <Popup>
        <article className="business-popup">
          {isDemo && <span className="mock-data-label">Demo data</span>}
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
          </dl>
          <EvidenceDetails sources={businessSources} label="Evidence" />
        </article>
      </Popup>
    </CircleMarker>
  );
}

export default BusinessMarker;
