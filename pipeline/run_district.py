#!/usr/bin/env python3
"""Run the PRAHARI disease-risk pipeline for a single district."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from adapters.weather import (
    build_node_lattice,
    fetch_nodes,
    load_cache,
    save_cache,
)
from engine.interpolate import bilinear
from engine.score import DiseaseModel, band, score_cell

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


if __name__ == "__main__":
    main()
