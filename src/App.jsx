import Header from './components/Header';
import InsightsPanel from './components/InsightsPanel';
import MapPanel from './components/MapPanel';
import QueryPanel from './components/QueryPanel';

function App() {
  return (
    <div className="app-shell">
      <Header />
      <main className="workspace">
        <QueryPanel />
        <div className="content-grid">
          <MapPanel />
          <InsightsPanel />
        </div>
      </main>
    </div>
  );
}

export default App;
