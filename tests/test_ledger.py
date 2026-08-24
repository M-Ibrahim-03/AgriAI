"""Tests for adapters/ledger.py — hash-chained append-only ledger."""

import json
import tempfile
from pathlib import Path

from adapters.ledger import append_run, verify_chain, summarise


def _make_record(run_id: str, cells_red: int = 0) -> dict:
    return {
        "run_id": run_id,
        "district": "Firozabad",
        "model_version": "1.0",
        "engine_git_sha": "abc123",
        "cells_total": 3600,
        "cells_amber": 100,
        "cells_red": cells_red,
        "red_cell_ids": [],
    }


# ── append + verify round-trip ───────────────────────────────────────

def test_append_and_verify():
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        path = f.name

    try:
        h1 = append_run(_make_record("2026-01-14T02:00:00+05:30", cells_red=50), path)
        h2 = append_run(_make_record("2026-01-15T02:00:00+05:30", cells_red=80), path)
        h3 = append_run(_make_record("2026-01-16T02:00:00+05:30", cells_red=20), path)

        assert len(h1) == 64  # SHA-256 hex digest
        assert h1 != h2 != h3

        ok, msg = verify_chain(path)
        assert ok is True
        assert "3 records verified" in msg
    finally:
        Path(path).unlink(missing_ok=True)


# ── GENESIS prev_hash for first record ──────────────────────────────

def test_genesis_prev_hash():
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        path = f.name
    try:
        append_run(_make_record("2026-01-14T02:00:00+05:30"), path)
        line = Path(path).read_text().strip().splitlines()[0]
        record = json.loads(line)
        assert record["prev_hash"] == "GENESIS"
    finally:
        Path(path).unlink(missing_ok=True)


# ── chain links correctly ───────────────────────────────────────────

def test_chain_links():
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        path = f.name
    try:
        h1 = append_run(_make_record("2026-01-14T02:00:00+05:30"), path)
        h2 = append_run(_make_record("2026-01-15T02:00:00+05:30"), path)
        lines = Path(path).read_text().strip().splitlines()
        rec2 = json.loads(lines[1])
        assert rec2["prev_hash"] == h1
    finally:
        Path(path).unlink(missing_ok=True)


# ── corruption detection ────────────────────────────────────────────

def test_corrupt_middle_record_detected():
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        path = f.name
    try:
        append_run(_make_record("2026-01-14T02:00:00+05:30", cells_red=10), path)
        append_run(_make_record("2026-01-15T02:00:00+05:30", cells_red=20), path)
        append_run(_make_record("2026-01-16T02:00:00+05:30", cells_red=30), path)

        # Corrupt the middle record's data
        lines = Path(path).read_text().strip().splitlines()
        rec = json.loads(lines[1])
        rec["cells_red"] = 999  # tamper
        lines[1] = json.dumps(rec, sort_keys=True, separators=(",", ":"))
        Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")

        ok, msg = verify_chain(path)
        assert ok is False
        assert "BROKEN" in msg
        assert "line 2" in msg or "line 3" in msg
    finally:
        Path(path).unlink(missing_ok=True)


# ── summarise ────────────────────────────────────────────────────────

def test_summarise():
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        path = f.name
    try:
        append_run(_make_record("2026-01-14T02:00:00+05:30", cells_red=10), path)
        append_run(_make_record("2026-01-16T02:00:00+05:30", cells_red=30), path)
        s = summarise(path)
        assert s["total_runs"] == 2
        assert s["total_red_alerts"] == 40
        assert s["date_range"] == ("2026-01-14T02:00:00+05:30", "2026-01-16T02:00:00+05:30")
    finally:
        Path(path).unlink(missing_ok=True)


# ── empty / missing file ────────────────────────────────────────────

def test_verify_missing_file():
    ok, msg = verify_chain("/tmp/nonexistent_ledger_test.jsonl")
    assert ok is False


def test_summarise_missing_file():
    s = summarise("/tmp/nonexistent_ledger_test.jsonl")
    assert s["total_runs"] == 0
