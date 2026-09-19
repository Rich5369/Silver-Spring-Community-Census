const pipelineSteps = [
  'Public data sources',
  'Backend ingestion / processing',
  'Normalized data / API',
  'Query layer',
  'Interactive map',
  'Evidence-linked result',
];

const plannedSources = [
  'U.S. Census Bureau / American Community Survey',
  'Montgomery County open data',
  'GIS and geographic boundary data',
  'Local business data',
];

function AboutData() {
  return (
    <details className="about-data">
      <summary><span aria-hidden="true">ⓘ</span> About this data</summary>
      <div className="about-data-content">
        <p>
          The MVP uses demo community and business records through the same frontend contract
          intended for a future backend. OpenStreetMap currently provides the basemap.
        </p>

        <strong className="pipeline-label">Target data flow</strong>
        <ol className="data-pipeline" aria-label="Target data flow">
          {pipelineSteps.map((step) => <li key={step}>{step}</li>)}
        </ol>

        <div className="planned-sources">
          <strong>Expected source categories</strong>
          <ul>
            {plannedSources.map((source) => <li key={source}>{source}</li>)}
          </ul>
          <p className="connection-status">
            Planned sources — not connected or presented as verified data yet.
          </p>
        </div>
      </div>
    </details>
  );
}

export default AboutData;
