import { useState, useRef, useEffect } from "react";

interface CellData {
  risk: number;
  band: string;
  accumulated_dsv: number;
  criterion_alert: boolean;
  reason: string;
  confidence: number;
  confidence_label: string;
  spray_start_hour: number | null;
  spray_end_hour: number | null;
}

interface InfoPanelProps {
  cell: CellData | null;
  onClose: () => void;
}

const BAND_BG: Record<string, string> = {
  green: "#22c55e",
  amber: "#f59e0b",
  red: "#ef4444",
};

function pickAudioKey(cell: CellData): string {
  const hasSpray = cell.spray_start_hour !== null;
  if (cell.band === "green") return hasSpray ? "green_soon" : "green_none";
  if (cell.band === "red") return hasSpray ? "red_now" : "red_nowindow";
  // amber
  return hasSpray ? "amber_now" : "amber_wait";
}

function pickSpraySlug(cell: CellData): string | null {
  const h = cell.spray_start_hour;
  if (h === null) return null;
  if (h < 12) return "aaj_shaam";
  if (h < 24) return "kal_subah_6_baje";
  if (h < 48) return "mangalvaar_subah";
  return "parso_subah";
}

export default function InfoPanel({ cell, onClose }: InfoPanelProps) {
  const [index, setIndex] = useState<Record<string, Record<string, string>>>({});
  const [playing, setPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    fetch("/audio/index.json")
      .then((r) => r.json())
      .then(setIndex)
      .catch(() => {});
  }, []);

  useEffect(() => {
    setPlaying(false);
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
  }, [cell]);

  if (!cell) return null;

  const handleListen = () => {
    if (playing && audioRef.current) {
      audioRef.current.pause();
      setPlaying(false);
      return;
    }

    const msgKey = pickAudioKey(cell);
    const slug = pickSpraySlug(cell);
    const variants = index[msgKey];
    if (!variants) return;

    const filename = slug && variants[slug] ? variants[slug] : variants["original"];
    if (!filename) return;

    const audio = new Audio(`/audio/${filename}`);
    audioRef.current = audio;
    audio.onended = () => setPlaying(false);
    audio.onerror = () => setPlaying(false);
    audio.play().then(() => setPlaying(true)).catch(() => {});
  };

  return (
    <div className="info-panel">
      <button className="info-close" onClick={onClose} aria-label="Close">
        ✕
      </button>

      <div className="info-header">
        <span
          className="info-badge"
          style={{ backgroundColor: BAND_BG[cell.band] ?? "#888" }}
        >
          {cell.band.toUpperCase()}
        </span>
        <span className="info-risk">
          Risk: {(cell.risk * 100).toFixed(0)}%
        </span>
        <span className={`info-conf info-conf-${cell.confidence_label}`}>
          {cell.confidence_label}
        </span>
      </div>

      <div className="info-body">
        <div className="info-row">
          <span className="info-label">Accumulated DSV</span>
          <span className="info-value">{cell.accumulated_dsv}</span>
        </div>
        <div className="info-row">
          <span className="info-label">Criterion alert</span>
          <span className="info-value">
            {cell.criterion_alert ? "⚠ Yes" : "No"}
          </span>
        </div>
        <div className="info-row">
          <span className="info-label">Confidence</span>
          <span className="info-value">{(cell.confidence * 100).toFixed(0)}%</span>
        </div>
        <p className="info-reason">{cell.reason}</p>
        {cell.confidence_label === "low" && (
          <p className="info-confidence-warn">
            ⚠️ Lower confidence here - our nearest weather points disagree. Worth checking your field directly.
          </p>
        )}

        <button className="info-listen-btn" onClick={handleListen}>
          <svg className="info-listen-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            {playing ? (
              <>
                <rect x="6" y="4" width="4" height="16" rx="1" fill="currentColor" stroke="none" />
                <rect x="14" y="4" width="4" height="16" rx="1" fill="currentColor" stroke="none" />
              </>
            ) : (
              <>
                <polygon points="5,3 19,12 5,21" fill="currentColor" stroke="none" />
              </>
            )}
          </svg>
          {playing ? "Ruk ja (Pause)" : "Suniye (Listen)"}
        </button>
      </div>
    </div>
  );
}
