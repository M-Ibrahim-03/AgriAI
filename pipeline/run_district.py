#!/usr/bin/env python3
"""Run the PRAHARI disease-risk pipeline for a single district."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

from adapters.weather import (
    build_node_lattice,
    fetch_nodes,
    load_cache,
    save_cache,
)
from engine.interpolate import bilinear
from engine.score import DiseaseModel, band, score_cell
from engine.spray_window import find_spray_windows, best_window_before_risk, describe_window
from adapters.ledger import append_run

# ── Configuration ────────────────────────────────────────────────────

CONFIG = {
    "district": "Firozabad",
    "min_lat": 26.87,
    "max_lat": 27.40,
    "min_lon": 78.13,
    "max_lon": 78.66,
    "cell_size": 0.01,          # ~1 km
    "node_step": 0.1,           # ~10 km lattice for weather nodes
}

MODEL = DiseaseModel(name="Potato Late Blight")

_IST = timezone(timedelta(hours=5, minutes=30))

CACHE_PATH = Path("artefacts/weather_cache.json")
OUTPUT_PATH = Path("artefacts/risk.geojson")


# ── Helpers ──────────────────────────────────────────────────────────

def _cell_grid(
    min_lat: float, max_lat: float,
    min_lon: float, max_lon: float,
    cell_size: float,
) -> list[tuple[float, float]]:
    """Return the SW corner of every 1 km cell in the bounding box."""
    cells: list[tuple[float, float]] = []
    lat = min_lat
    while lat < max_lat:
        lon = min_lon
        while lon < max_lon:
            cells.append((round(lat, 6), round(lon, 6)))
            lon += cell_size
        lat += cell_size
    return cells


def _reshape_to_days(hourly: list[float], hours_per_day: int = 24) -> list[list[float]]:
    """Chop a flat hourly list into per-day sub-lists."""
    return [
        hourly[i : i + hours_per_day]
        for i in range(0, len(hourly), hours_per_day)
        if len(hourly[i : i + hours_per_day]) == hours_per_day
    ]


def _square_geojson(lat: float, lon: float, size: float) -> list[list[list[float]]]:
    """Return a GeoJSON Polygon coordinates for a square cell."""
    return [[
        [lon, lat],
        [lon + size, lat],
        [lon + size, lat + size],
        [lon, lat + size],
        [lon, lat],
    ]]


def _summary(counts: dict[str, int], total: int) -> str:
    lines = [f"Total cells scored: {total}"]
    for colour in ("green", "amber", "red"):
        n = counts.get(colour, 0)
        pct = n / total * 100 if total else 0
        lines.append(f"  {colour:>5s}: {n:>4d}  ({pct:5.1f}%)")
    return "\n".join(lines)


# ── Main ─────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="PRAHARI district risk scorer")
    parser.add_argument(
        "--refresh", action="store_true",
        help="Re-fetch weather data from Open-Meteo instead of using the cache",
    )
    args = parser.parse_args()

    # 1. Node lattice for weather data
    nodes = build_node_lattice(
        CONFIG["min_lat"], CONFIG["max_lat"],
        CONFIG["min_lon"], CONFIG["max_lon"],
        step=CONFIG["node_step"],
    )
    print(f"Node lattice: {len(nodes)} points")

    # 2. Weather data
    if args.refresh:
        print("Fetching from Open-Meteo …")
        weather = fetch_nodes(nodes)
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        save_cache(weather, str(CACHE_PATH))
        print(f"Cached {len(weather)} nodes → {CACHE_PATH}")
    else:
        if not CACHE_PATH.exists():
            print(f"Cache not found at {CACHE_PATH}; fetching …")
            weather = fetch_nodes(nodes)
            CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            save_cache(weather, str(CACHE_PATH))
        else:
            weather = load_cache(str(CACHE_PATH))
            print(f"Loaded {len(weather)} nodes from {CACHE_PATH}")

    # 3. Cell grid
    cells = _cell_grid(
        CONFIG["min_lat"], CONFIG["max_lat"],
        CONFIG["min_lon"], CONFIG["max_lon"],
        CONFIG["cell_size"],
    )
    print(f"Scoring {len(cells)} cells …")

    # 4. Score every cell
    features: list[dict] = []
    band_counts: dict[str, int] = {}

    for lat, lon in cells:
        interp = bilinear(lat, lon, weather)
        rh_days = _reshape_to_days(interp["rh"])
        temp_days = _reshape_to_days(interp["temp"])

        risk_result = score_cell(rh_days, temp_days, MODEL)
        colour = band(risk_result.risk)
        band_counts[colour] = band_counts.get(colour, 0) + 1

        # -- Spray window --
        _precip = interp.get("precip", [])
        _wind = interp.get("wind", [])
        _spray_wins = find_spray_windows(_precip, _wind, interp["temp"])

        _hours_until = len(rh_days) * 24
        for _d in range(len(rh_days)):
            _r = score_cell(rh_days[: _d + 1], temp_days[: _d + 1], MODEL)
            if _r.risk >= 0.45:
                _hours_until = _d * 24
                break

        _best = best_window_before_risk(_spray_wins, _hours_until)

        if _best is not None:
            _day_names = [f"Day {i + 1}" for i in range(len(rh_days))]
            _spray_text = describe_window(_best, _day_names)
            _spray_start: int | None = _best.start_index
            _spray_end: int | None = _best.end_index
            _spray_quality: float | None = _best.quality
        else:
            _spray_text = "No good spray window in the next 3 days"
            _spray_start = None
            _spray_end = None
            _spray_quality = None

        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": _square_geojson(lat, lon, CONFIG["cell_size"]),
            },
            "properties": {
                "risk": risk_result.risk,
                "band": colour,
                "accumulated_dsv": risk_result.accumulated_dsv,
                "criterion_alert": risk_result.criterion_alert,
                "reason": risk_result.reason,
                "spray_start_hour": _spray_start,
                "spray_end_hour": _spray_end,
                "spray_quality": _spray_quality,
                "spray_text": _spray_text,
            },
        })

    # 5. Write GeoJSON
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps({
        "type": "FeatureCollection",
        "features": features,
    }, indent=2))
    print(f"\nWrote {OUTPUT_PATH}")

    # 6. Summary
    print(_summary(band_counts, len(features)))

    # 7. Spray-window summary
    _spray_24h = sum(
        1 for f in features
        if f["properties"]["spray_start_hour"] is not None
        and f["properties"]["spray_start_hour"] < 24
    )
    print(f"Cells with spray window in next 24h: {_spray_24h}/{len(features)}")

    # 8. Ledger record
    _sha = os.environ.get("GITHUB_SHA")
    if not _sha:
        try:
            _sha = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True, text=True, timeout=5,
            ).stdout.strip()
        except Exception:
            _sha = "unknown"
    if not _sha:
        _sha = "unknown"

    _run_id = datetime.now(_IST).isoformat()
    _mv = f"rh{MODEL.rh_threshold:.0f}_h{MODEL.min_wet_hours}_t{MODEL.min_temp_c:.0f}_c{MODEL.consecutive_days}_s{MODEL.spray_threshold_dsv}"

    _ledger_hash = append_run({
        "run_id": _run_id,
        "district": CONFIG["district"],
        "model_version": _mv,
        "engine_git_sha": _sha,
        "cells_total": len(features),
        "cells_amber": band_counts.get("amber", 0),
        "cells_red": band_counts.get("red", 0),
        "red_cell_ids": [],
    })
    print(f"Ledger hash: {_ledger_hash}")


if __name__ == "__main__":
    main()
