import { useEffect, useMemo, useState } from 'react';
import ComparisonTable from './ComparisonTable';
import { buildComparisonRows, getComparisonAreaId } from '../services/comparisonAdapter';

function ComparisonPanel({ areas = [] }) {
  const options = useMemo(() => {
    const uniqueAreas = new Map();
    areas.filter(Boolean).forEach((area) => uniqueAreas.set(getComparisonAreaId(area), area));
    return [...uniqueAreas.entries()].map(([id, area]) => ({ id, area }));
  }, [areas]);
  const [leftId, setLeftId] = useState('');
  const [rightId, setRightId] = useState('');

  useEffect(() => {
    if (!options.some((option) => option.id === leftId)) {
      setLeftId(options[0]?.id ?? '');
    }
    if (!options.some((option) => option.id === rightId) || rightId === leftId) {
      setRightId('');
    }
  }, [leftId, options, rightId]);

  const leftArea = options.find((option) => option.id === leftId)?.area;
  const rightArea = options.find((option) => option.id === rightId)?.area;
  const rows = buildComparisonRows(leftArea, rightArea);

  return (
    <details className="comparison-panel">
      <summary>Compare Areas</summary>
      <div className="comparison-content">
        <div className="comparison-selectors">
          <label>
            Area one
            <select value={leftId} onChange={(event) => setLeftId(event.target.value)}>
              {options.map((option) => (
                <option value={option.id} key={option.id}>{option.area.areaName}</option>
              ))}
            </select>
          </label>
          <label>
            Area two
            <select
              value={rightId}
              disabled={options.length < 2}
              onChange={(event) => setRightId(event.target.value)}
            >
              <option value="">
                {options.length < 2 ? 'No other area available' : 'Select an area'}
              </option>
              {options.filter((option) => option.id !== leftId).map((option) => (
                <option value={option.id} key={option.id}>{option.area.areaName}</option>
              ))}
            </select>
          </label>
        </div>

        {leftArea && rightArea
          ? <ComparisonTable leftArea={leftArea} rightArea={rightArea} rows={rows} />
          : <p className="comparison-empty">Connect or select another real area to compare.</p>}
      </div>
    </details>
  );
}

export default ComparisonPanel;
