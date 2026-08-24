interface CellData {
  risk: number;
  band: string;
  accumulated_dsv: number;
  criterion_alert: boolean;
  reason: string;
  confidence: number;
  confidence_label: string;
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

export default function InfoPanel({ cell, onClose }: InfoPanelProps) {
  if (!cell) return null;

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
      </div>
    </div>
  );
}
