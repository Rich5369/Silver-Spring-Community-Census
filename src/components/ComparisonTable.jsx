function ComparisonTable({ leftArea, rightArea, rows = [] }) {
  return (
    <div className="comparison-table-wrap">
      <table className="comparison-table">
        <thead>
          <tr>
            <th scope="col">Metric</th>
            <th scope="col">{leftArea.areaName}</th>
            <th scope="col">{rightArea.areaName}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr className={row.comparable ? '' : 'comparison-unavailable'} key={row.id}>
              <th scope="row">{row.label}</th>
              <td>{row.leftValue}</td>
              <td>{row.rightValue}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length === 0 && (
        <p className="empty-data-message">No shared metric fields are available.</p>
      )}
      <p className="comparison-note">
        Values are comparable only when both areas provide the metric.
      </p>
    </div>
  );
}

export default ComparisonTable;
