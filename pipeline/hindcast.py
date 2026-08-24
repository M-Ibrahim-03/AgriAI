#!/usr/bin/env python3
"""Hindcast evaluation: score historical events against ground truth."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import requests
import yaml

from engine.interpolate import bilinear
from engine.score import DiseaseModel, band, score_cell

# ── Config ───────────────────────────────────────────────────────────

GROUND_TRUTH_PATH = Path("artefacts/ground_truth.yaml")
CACHE_DIR = Path("artefacts/hindcast_cache")
OUTPUT_PATH = Path("artefacts/hindcast_result.json")

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
REQUEST_TIMEOUT = 30
LOOKBACK_DAYS = 14

MODEL = DiseaseModel(name="Potato Late Blight Hindcast")


# ── Archive fetch with caching ──────────────────────────────────────

def _cache_path(lat: float, lon: float, start: str, end: str) -> Path:
    return CACHE_DIR / f"{lat}_{lon}_{start}_{end}.json"


def fetch_archive(
    lat: float, lon: float, start_date: str, end_date: str
) -> dict:
    """Fetch hourly weather from Open-Meteo archive API, with local cache."""
    cp = _cache_path(lat, lon, start_date, end_date)
    if cp.exists():
        return json.loads(cp.read_text())

    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": "relative_humidity_2m,temperature_2m",
    }
    resp = requests.get(ARCHIVE_URL, params=params, timeout=REQUEST_TIMEOUT)
    if resp.status_code != 200:
        raise RuntimeError(
            f"Archive API HTTP {resp.status_code}: {resp.text[:200]}"
        )
    data = resp.json()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cp.write_text(json.dumps(data))
    return data


def archive_to_nodes(data: dict) -> dict[tuple[float, float], dict]:
    """Convert archive JSON response into the node dict format expected by bilinear."""
    hourly = data.get("hourly", {})
    return {
        (data["latitude"], data["longitude"]): {
            "rh": hourly.get("relative_humidity_2m", []),
            "temp": hourly.get("temperature_2m", []),
            "time": hourly.get("time", []),
        }
    }


# ── Reshape & score ─────────────────────────────────────────────────

def _reshape_to_days(hourly: list[float], hours_per_day: int = 24) -> list[list[float]]:
    return [
        hourly[i : i + hours_per_day]
        for i in range(0, len(hourly), hours_per_day)
        if len(hourly[i : i + hours_per_day]) == hours_per_day
    ]


def _to_date_str(val) -> str:
    """Coerce datetime.date, datetime, or str to YYYY-MM-DD string."""
    if isinstance(val, str):
        return val
    return val.strftime("%Y-%m-%d")


def score_event(lat: float, lon: float, event_date: str) -> dict:
    """Fetch 14-day window, score it, return per-day detail."""
    dt = datetime.strptime(event_date, "%Y-%m-%d")
    start = (dt - timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%d")
    end = (dt - timedelta(days=1)).strftime("%Y-%m-%d")

    raw = fetch_archive(lat, lon, start, end)
    nodes = archive_to_nodes(raw)
    interp = bilinear(lat, lon, nodes)

    rh_days = _reshape_to_days(interp["rh"])
    temp_days = _reshape_to_days(interp["temp"])

    result = score_cell(rh_days, temp_days, MODEL)

    return {
        "risk": result.risk,
        "band": band(result.risk),
        "accumulated_dsv": result.accumulated_dsv,
        "criterion_alert": result.criterion_alert,
        "reason": result.reason,
        "days_scored": len(rh_days),
    }


# ── Main ─────────────────────────────────────────────────────────────

def main() -> None:
    with open(GROUND_TRUTH_PATH) as f:
        events = yaml.safe_load(f)

    hits = 0
    misses = 0
    false_alarms = 0
    correct_negatives = 0
    results = []

    for ev in events:
        label = ev["label"]
        lat, lon = ev["lat"], ev["lon"]
        date = _to_date_str(ev["date"])
        place = ev["place"]

        print(f"Scoring {place} ({date}) ...", end=" ", flush=True)

        scored = score_event(lat, lon, date)
        predicted_red = scored["band"] == "red"

        if label == 1 and predicted_red:
            outcome = "hit"
            hits += 1
        elif label == 1 and not predicted_red:
            outcome = "miss"
            misses += 1
        elif label == 0 and predicted_red:
            outcome = "false_alarm"
            false_alarms += 1
        else:
            outcome = "correct_negative"
            correct_negatives += 1

        print(outcome)

        results.append({
            "lat": lat,
            "lon": lon,
            "place": place,
            "date": date,
            "label": label,
            "predicted_band": scored["band"],
            "outcome": outcome,
            **scored,
        })

    # ── Contingency table ────────────────────────────────────────────
    total = hits + misses + false_alarms + correct_negatives
    pod = hits / (hits + misses) if (hits + misses) else 0.0
    far = false_alarms / (hits + false_alarms) if (hits + false_alarms) else 0.0
    csi = hits / (hits + misses + false_alarms) if (hits + misses + false_alarms) else 0.0

    print("\n" + "=" * 50)
    print("CONTINGENCY TABLE")
    print("=" * 50)
    print(f"  Hits (TP):              {hits}")
    print(f"  Misses (FN):            {misses}")
    print(f"  False Alarms (FP):      {false_alarms}")
    print(f"  Correct Negatives (TN): {correct_negatives}")
    print(f"  Total:                  {total}")
    print("-" * 50)
    print(f"  POD (Probability of Detection): {pod:.3f}")
    print(f"  FAR (False Alarm Ratio):        {far:.3f}")
    print(f"  CSI (Critical Success Index):   {csi:.3f}")
    print("=" * 50)

    # ── Write result ─────────────────────────────────────────────────
    output = {
        "contingency": {
            "hits": hits,
            "misses": misses,
            "false_alarms": false_alarms,
            "correct_negatives": correct_negatives,
        },
        "metrics": {
            "pod": round(pod, 4),
            "far": round(far, 4),
            "csi": round(csi, 4),
        },
        "model": {
            "name": MODEL.name,
            "rh_threshold": MODEL.rh_threshold,
            "min_wet_hours": MODEL.min_wet_hours,
            "min_temp_c": MODEL.min_temp_c,
            "consecutive_days": MODEL.consecutive_days,
            "spray_threshold_dsv": MODEL.spray_threshold_dsv,
        },
        "events": results,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, indent=2))
    print(f"\nWrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
