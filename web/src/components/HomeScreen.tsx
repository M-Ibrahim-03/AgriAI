import { useState, useEffect, useRef } from "react";

interface Feature {
  geometry: { coordinates: number[][][] };
  properties: {
    risk: number;
    band: string;
    accumulated_dsv: number;
    criterion_alert: boolean;
    reason: string;
    spray_text: string;
  };
}

interface GeoJSON {
  features: Feature[];
}

const BAND_META: Record<string, { headline: string; bg: string; text: string }> = {
  green: { headline: "Sab theek hai", bg: "#166534", text: "#ffffff" },
  amber: { headline: "Savdhan rahein", bg: "#78350f", text: "#ffffff" },
  red:   { headline: "Khatra bahut zyada", bg: "#991b1b", text: "#ffffff" },
};

function computeDistrictSummary(geojson: GeoJSON): {
  band: string;
  sprayText: string;
} {
  const counts = { green: 0, amber: 0, red: 0 };
  const sprayTexts: Record<string, number> = {};

  for (const f of geojson.features) {
    const b = f.properties.band as keyof typeof counts;
    if (b in counts) counts[b]++;
    const st = f.properties.spray_text;
    sprayTexts[st] = (sprayTexts[st] || 0) + 1;
  }

  let worstBand = "green";
  if (counts.red > 0) worstBand = "red";
  else if (counts.amber > 0) worstBand = "amber";

  const topText = Object.entries(sprayTexts).sort((a, b) => b[1] - a[1])[0]?.[0] ?? "";

  return { band: worstBand, sprayText: topText };
}

export default function HomeScreen() {
  const [summary, setSummary] = useState<{ band: string; sprayText: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [playing, setPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    fetch("/risk.geojson")
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data: GeoJSON) => {
        setSummary(computeDistrictSummary(data));
        setLoading(false);
      })
      .catch((e) => {
        setError(e.message || "Data load failed");
        setLoading(false);
      });
  }, []);

  const handleListen = () => {
    if (playing && audioRef.current) {
      audioRef.current.pause();
      setPlaying(false);
      return;
    }

    const band = summary?.band ?? "green";
    const audioKey =
      band === "red" ? "red_now" :
      band === "amber" ? "amber_now" :
      "green_none";

    fetch("/audio/index.json")
      .then((r) => r.json())
      .then((index) => {
        const variants = index[audioKey];
        if (!variants) return;
        const filename = variants["original"] ?? Object.values(variants)[0];
        if (!filename) return;
        const audio = new Audio(`/audio/${filename}`);
        audioRef.current = audio;
        audio.onended = () => setPlaying(false);
        audio.onerror = () => setPlaying(false);
        audio.play().then(() => setPlaying(true)).catch(() => {});
      })
      .catch(() => {});
  };

  if (loading) {
    return (
      <div className="home">
        <div className="home-loading">
          <div className="skeleton-spinner" />
          <span className="skeleton-text">Loading…</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="home">
        <div className="home-error">
          <div className="error-icon">⚠</div>
          <div className="error-title">Data nahi mil payi</div>
          <div className="error-msg">{error}</div>
        </div>
      </div>
    );
  }

  const band = summary?.band ?? "green";
  const meta = BAND_META[band];

  return (
    <div className="home">
      <div className="home-status" style={{ background: meta.bg, color: meta.text }}>
        <div className="home-label">Aaj ka khatra</div>
        <div className="home-headline">{meta.headline}</div>
        <div className="home-spray">{summary?.sprayText}</div>
      </div>

      <div className="home-tiles">
        <a href="/map" className="home-tile">
          <svg className="home-tile-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M1 6v16l7-4 8 4 7-4V2l-7 4-8-4-7 4z" />
            <path d="M8 2v16M16 6v16" />
          </svg>
          Map
        </a>

        <button className="home-tile" onClick={() => {
          const el = document.querySelector(".home-explain");
          if (el) el.classList.toggle("home-explain-open");
        }}>
          <svg className="home-tile-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <path d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3M12 17h.01" />
          </svg>
          Why?
        </button>

        <button className="home-tile" onClick={handleListen}>
          <svg className="home-tile-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            {playing ? (
              <>
                <rect x="6" y="4" width="4" height="16" rx="1" fill="currentColor" stroke="none" />
                <rect x="14" y="4" width="4" height="16" rx="1" fill="currentColor" stroke="none" />
              </>
            ) : (
              <polygon points="5,3 19,12 5,21" fill="currentColor" stroke="none" />
            )}
          </svg>
          {playing ? "Ruk ja" : "Suniye"}
        </button>
      </div>

      <div className="home-explain">
        <p>
          <strong>Khatra kaise tay hota hai?</strong><br />
          Hum teen cheezein dekhte hain: kitni der nami rahi (umidity),
          kitni thandi hai (temperature), aur lagatar kitne din khatra badha.
          Jab ye teeno mil jaayein — chhidkaav ka waqt aa gaya.
        </p>
        <p>
          <strong>Colour ka matlab:</strong><br />
          <span style={{ color: "#166534" }}>●</span> Green — abhi khatra kam hai.
          {" "}
          <span style={{ color: "#78350f" }}>●</span> Amber — savdhan, khatra badh raha hai.
          {" "}
          <span style={{ color: "#991b1b" }}>●</span> Red — turant chhidkaav kijiye.
        </p>
      </div>

      <div className="home-footer">
        PRAHARI · Firozabad
      </div>
    </div>
  );
}
