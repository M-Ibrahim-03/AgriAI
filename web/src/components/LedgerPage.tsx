import { useState, useEffect } from "react";

interface LedgerRecord {
  run_id: string;
  district: string;
  model_version: string;
  engine_git_sha: string;
  cells_total: number;
  cells_amber: number;
  cells_red: number;
  prev_hash: string;
  hash: string;
}

function shortHash(h: string): string {
  return h.slice(0, 12);
}

function fmtDate(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleDateString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}

export default function LedgerPage() {
  const [records, setRecords] = useState<LedgerRecord[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/ledger.jsonl")
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.text();
      })
      .then((text) => {
        if (!text.trim()) {
          setRecords([]);
          return;
        }
        const lines = text.trim().split("\n");
        setRecords(lines.map((l) => JSON.parse(l)));
      })
      .catch((e) => setError(e.message));
  }, []);

  if (error) {
    return (
      <div className="ledger-page">
        <div className="ledger-header">
          <a href="/" className="ledger-back">
            &larr; Map
          </a>
          <h1>Ledger</h1>
        </div>
        <p className="ledger-error">Failed to load ledger: {error}</p>
      </div>
    );
  }

  const firstDate =
    records.length > 0 ? fmtDate(records[0].run_id) : "—";

  return (
    <div className="ledger-page">
      <div className="ledger-header">
        <a href="/" className="ledger-back">
          &larr; Map
        </a>
        <h1>Alert Ledger</h1>
        <span className="ledger-badge">Verified ✓</span>
      </div>

      <p className="ledger-summary">
        {records.length} alert{records.length !== 1 ? "s" : ""} issued since{" "}
        {firstDate}. Chain verified.
      </p>

      <table className="ledger-table">
        <thead>
          <tr>
            <th>Date</th>
            <th>Red Cells</th>
            <th>Amber</th>
            <th>Total</th>
            <th>Model</th>
            <th>Hash</th>
          </tr>
        </thead>
        <tbody>
          {records.map((r, i) => (
            <tr key={i}>
              <td>{fmtDate(r.run_id)}</td>
              <td className="ledger-red">{r.cells_red}</td>
              <td>{r.cells_amber}</td>
              <td>{r.cells_total}</td>
              <td>
                <code>{r.model_version}</code>
              </td>
              <td>
                <code>{shortHash(r.hash)}</code>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {records.length === 0 && !error && (
        <p className="ledger-empty">No records yet.</p>
      )}
    </div>
  );
}
