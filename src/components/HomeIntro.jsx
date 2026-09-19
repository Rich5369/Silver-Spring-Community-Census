const capabilities = [
  { title: 'Explore communities', text: 'Select Census areas and understand the people who live there.' },
  { title: 'Understand local businesses', text: 'Search and filter connected business records around Fenton Village.' },
  { title: 'Analyze planning trends', text: 'Review supported population, income, and community indicators over time.' },
  { title: 'Trace the evidence', text: 'See the public datasets behind important statistics and answers.' },
];

export default function HomeIntro({ onExplore, onExploreFenton }) {
  return (
    <section className="home-intro" aria-labelledby="home-intro-title">
      <div className="hero-copy">
        <p className="eyebrow">Community intelligence for Silver Spring</p>
        <h2 id="home-intro-title">Understand the community behind the map.</h2>
        <p className="hero-lede">
          Explore Census trends, local businesses, housing, transportation, and public evidence
          in one connected place.
        </p>
        <div className="hero-actions">
          <button className="primary-button" type="button" onClick={onExplore}>Explore the map</button>
          <button className="secondary-button" type="button" onClick={onExploreFenton}>Explore Fenton Village</button>
        </div>
        <p className="hero-audience">Built to help planners and communities understand local conditions through public evidence.</p>
      </div>
      <div className="home-purpose">
        <p>
          Public information about Silver Spring is spread across Census records, geographic
          layers, business data, and planning sources. This tool brings that evidence together
          in one interactive community map.
        </p>
        <div className="capability-grid">
          {capabilities.map((capability) => (
            <article key={capability.title}>
              <h3>{capability.title}</h3>
              <p>{capability.text}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

