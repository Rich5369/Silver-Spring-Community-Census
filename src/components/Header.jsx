function Header() {
  return (
    <header className="site-header">
      <div className="brand-mark" aria-hidden="true">SS</div>
      <div className="brand-copy">
        <p className="eyebrow">Community intelligence</p>
        <h1>Silver Spring Community Census</h1>
      </div>
      <div className="location-label">
        <span className="location-full">Silver Spring, Maryland</span>
        <span className="location-short">Silver Spring, MD</span>
      </div>
    </header>
  );
}

export default Header;
