import { useState, useEffect, useCallback } from "react";
import MapPanel from "./components/MapPanel";
import InfoPanel from "./components/InfoPanel";
import TimeSlider from "./components/TimeSlider";
import LedgerPage from "./components/LedgerPage";
import "./App.css";

const GEOJSON_URLS = [
  "/risk.geojson",
  "/risk_d3.geojson",
  "/risk_d7.geojson",
];

interface Feature {
  geometry: { coordinates: number[][][] };
  properties: {
    risk: number;
    band: string;
    accumulated_dsv: number;
    criterion_alert: boolean;
    reason: string;
  };
}

interface GeoJSON {
  features: Feature[];
}

function MapApp() {
  const [timeIndex, setTimeIndex] = useState(0);
  const [geojson, setGeojson] = useState<GeoJSON | null>(null);
  const [selected, setSelected] = useState<Feature | null>(null);

  useEffect(() => {
    setSelected(null);
    fetch(GEOJSON_URLS[timeIndex])
      .then((r) => r.json())
      .then((data: GeoJSON) => setGeojson(data))
      .catch(console.error);
  }, [timeIndex]);

  const handleSelect = useCallback((f: Feature | null) => {
    setSelected(f);
  }, []);

  return (
    <div className="app">
      <div className="top-bar">
        <span className="top-bar-title">PRAHARI</span>
        <a href="/ledger" className="top-bar-link">
          Audit Log
        </a>
      </div>
      <MapPanel geojson={geojson} onSelect={handleSelect} />
      <TimeSlider value={timeIndex} onChange={setTimeIndex} />
      <InfoPanel cell={selected?.properties ?? null} onClose={() => setSelected(null)} />
    </div>
  );
}

function App() {
  const path = window.location.pathname;
  if (path === "/ledger") {
    return <LedgerPage />;
  }
  return <MapApp />;
}

export default App;
