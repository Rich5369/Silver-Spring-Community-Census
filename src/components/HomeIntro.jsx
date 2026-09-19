const capabilities = [
  { icon: '↗', title: 'Explore communities', text: 'Select Census areas, understand local conditions, and ask questions about the data.' },
  { icon: '◌', title: 'Understand local businesses', text: 'Search and filter connected business records around Fenton Village.' },
  { icon: '⌁', title: 'Analyze community trends', text: 'Review supported population, income, and community indicators over time.' },
  { icon: '⊙', title: 'Trace the evidence', text: 'See the public datasets behind important statistics and answers.' },
];

export default function HomeIntro({ onExplore, onViewTrends }) {
  return (
    <section className="home-intro" aria-labelledby="home-intro-title">
      <div className="hero-copy">
        <p className="eyebrow"><span className="eyebrow-dot" />Community intelligence for Silver Spring</p>
        <h2 id="home-intro-title">Understand the community behind the map.</h2>
        <p className="hero-lede">
          Explore Census trends, local businesses, housing, transportation, and public evidence
          in one connected place.
        </p>
        <div className="hero-actions">
          <button className="primary-button" type="button" onClick={onViewTrends}>View community trends</button>
          <button className="secondary-button" type="button" onClick={onExplore}>Explore the map</button>
        </div>
        <p className="hero-audience"><span aria-hidden="true">✦</span> Built for planners, residents, and council conversations grounded in public evidence.</p>
      </div>
      <div className="home-purpose">
        <p>
          <span className="purpose-kicker">One place to start a better civic conversation</span>
          Public information about Silver Spring is spread across Census records, geographic
          layers, business data, and planning sources. This tool brings that evidence together
          in one interactive community map.
        </p>
        <div className="capability-grid">
          {capabilities.map((capability) => (
            <article key={capability.title}>
              <span className="capability-icon" aria-hidden="true">{capability.icon}</span>
              <h3>{capability.title}</h3>
              <p>{capability.text}</p>
            </article>
          ))}
        </div>
      </div>
      <div className="hero-instrument" aria-hidden="true">
        <div className="instrument-orbit orbit-one" />
        <div className="instrument-orbit orbit-two" />
        <div className="instrument-core"><span>SS / 01</span><small>civic signal</small></div>
        <i className="instrument-point point-one" /><i className="instrument-point point-two" /><i className="instrument-point point-three" />
        <span className="instrument-caption">PUBLIC EVIDENCE / 2026</span>
      </div>
    </section>
  );
}
