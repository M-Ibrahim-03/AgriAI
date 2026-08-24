"""Hash-chained append-only ledger for nightly run records."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def _hash_record(record: dict) -> str:
    """SHA-256 of the canonical JSON of *record* (without the 'hash' key)."""
    payload = {k: v for k, v in record.items() if k != "hash"}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def append_run(record: dict, path: str = "artefacts/ledger.jsonl") -> str:
    """Append a run record to the ledger. Returns the new hash."""
    ledger = Path(path)
    prev_hash = "GENESIS"
    if ledger.exists() and ledger.stat().st_size > 0:
        last_line = ledger.read_text(encoding="utf-8").strip().splitlines()[-1]
        prev_hash = json.loads(last_line)["hash"]

    record["prev_hash"] = prev_hash
    record["hash"] = _hash_record(record)

    with open(ledger, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")

    return record["hash"]


def verify_chain(path: str = "artefacts/ledger.jsonl") -> tuple[bool, str]:
    """Walk the ledger and verify hash chain integrity."""
    ledger = Path(path)
    if not ledger.exists():
        return False, "File does not exist"

    lines = ledger.read_text(encoding="utf-8").strip().splitlines()
    if not lines:
        return False, "Empty ledger"

    prev_hash = "GENESIS"
    for i, line in enumerate(lines):
        record = json.loads(line)

        # Check prev_hash chain
        if record["prev_hash"] != prev_hash:
            return False, f"BROKEN at line {i + 1}: prev_hash mismatch"

        # Check content hash
        expected = _hash_record(record)
        if record["hash"] != expected:
            return False, f"BROKEN at line {i + 1}: content hash mismatch"

        prev_hash = record["hash"]

    return True, f"OK: {len(lines)} records verified"


def summarise(path: str = "artefacts/ledger.jsonl") -> dict:
    """Return aggregate stats across the entire ledger."""
    ledger = Path(path)
    if not ledger.exists():
        return {"total_runs": 0, "date_range": None, "total_red_alerts": 0}

    lines = ledger.read_text(encoding="utf-8").strip().splitlines()
    if not lines:
        return {"total_runs": 0, "date_range": None, "total_red_alerts": 0}

    records = [json.loads(line) for line in lines]
    dates = sorted(r["run_id"] for r in records)
    total_red = sum(r.get("cells_red", 0) for r in records)

    return {
        "total_runs": len(records),
        "date_range": (dates[0], dates[-1]),
        "total_red_alerts": total_red,
    }
