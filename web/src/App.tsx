import { useState, useEffect, useCallback } from "react";
import HomeScreen from "./components/HomeScreen";
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
    confidence: number;
    confidence_label: string;
    spray_start_hour: number | null;
    spray_end_hour: number | null;
    spray_text: string;
  };
}

interface GeoJSON {
  features: Feature[];
}

function MapView() {
  const [timeIndex, setTimeIndex] = useState(0);
  const [geojson, setGeojson] = useState<GeoJSON | null>(null);
  const [selected, setSelected] = useState<Feature | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setSelected(null);
    setLoading(true);
    setError(null);
    fetch(GEOJSON_URLS[timeIndex])
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data: GeoJSON) => {
        setGeojson(data);
        setLoading(false);
      })
      .catch((e) => {
        setError(e.message || "Failed to load risk data");
        setLoading(false);
      });
  }, [timeIndex]);

  const handleSelect = useCallback((f: Feature | null) => {
    setSelected(f);
  }, []);

  return (
    <div className="app">
      <div className="top-bar">
        <a href="/" className="top-bar-link">← Home</a>
        <span className="top-bar-title">PRAHARI</span>
        <a href="/ledger" className="top-bar-link">Audit Log</a>
      </div>
      <MapPanel geojson={geojson} onSelect={handleSelect} loading={loading} error={error} />
      <TimeSlider value={timeIndex} onChange={setTimeIndex} />
      <InfoPanel cell={selected?.properties ?? null} onClose={() => setSelected(null)} />
    </div>
  );
}

function App() {
  const path = window.location.pathname;
  if (path === "/ledger") return <LedgerPage />;
  if (path === "/map") return <MapView />;
  return <HomeScreen />;
}

export default App;
