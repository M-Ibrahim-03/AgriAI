#!/usr/bin/env python3
"""Grid-search DiseaseModel parameters against cached hindcast data."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timedelta
from itertools import product
from pathlib import Path

import yaml

from engine.interpolate import bilinear
from engine.score import DiseaseModel, band, score_cell

GROUND_TRUTH_PATH = Path("artefacts/ground_truth.yaml")
CACHE_DIR = Path("artefacts/hindcast_cache")
OUTPUT_PATH = Path("artefacts/calibration.csv")

LOOKBACK_DAYS = 14
COST_FALSE_ALARM = 500
COST_MISS = 40_000

PARAM_GRID = {
    "min_wet_hours": [4, 6, 8, 11],
    "min_temp_c": [8, 10, 12],
    "consecutive_days": [1, 2, 3],
    "spray_threshold_dsv": [12, 15, 18, 21],
}


def _to_date_str(val):
    if isinstance(val, str):
        return val
    return val.strftime("%Y-%m-%d")


def _reshape_to_days(hourly, hours_per_day=24):
    return [
        hourly[i : i + hours_per_day]
        for i in range(0, len(hourly), hours_per_day)
        if len(hourly[i : i + hours_per_day]) == hours_per_day
    ]


def _load_cached_event(lat, lon, event_date):
    dt = datetime.strptime(event_date, "%Y-%m-%d")
    start = (dt - timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%d")
    end = (dt - timedelta(days=1)).strftime("%Y-%m-%d")
    cp = CACHE_DIR / ("%s_%s_%s_%s.json" % (lat, lon, start, end))
    if not cp.exists():
        raise FileNotFoundError("Cache miss: " + str(cp))
    raw = json.loads(cp.read_text())
    hourly = raw.get("hourly", {})
    nodes = {
        (raw["latitude"], raw["longitude"]): {
            "rh": hourly.get("relative_humidity_2m", []),
            "temp": hourly.get("temperature_2m", []),
            "time": hourly.get("time", []),
        }
    }
    interp = bilinear(lat, lon, nodes)
    return {
        "rh_days": _reshape_to_days(interp["rh"]),
        "temp_days": _reshape_to_days(interp["temp"]),
    }


def main():
    with open(GROUND_TRUTH_PATH) as f:
        events = yaml.safe_load(f)

    print("Loading cached weather data ...")
    event_data = []
    for ev in events:
        lat, lon = ev["lat"], ev["lon"]
        date = _to_date_str(ev["date"])
        try:
            data = _load_cached_event(lat, lon, date)
            event_data.append({
                "label": ev["label"],
                "place": ev["place"],
                "rh_days": data["rh_days"],
                "temp_days": data["temp_days"],
            })
        except FileNotFoundError as e:
            print("  SKIP %s: %s" % (ev["place"], e))

    print("Loaded %d events" % len(event_data))
    print()

    keys = list(PARAM_GRID.keys())
    combos = list(product(*PARAM_GRID.values()))
    print("Testing %d parameter combinations ..." % len(combos))
    print()

    rows = []
    for i, vals in enumerate(combos, 1):
        params = dict(zip(keys, vals))
        model = DiseaseModel(
            name="calibration",
            min_wet_hours=params["min_wet_hours"],
            min_temp_c=params["min_temp_c"],
            consecutive_days=params["consecutive_days"],
            spray_threshold_dsv=params["spray_threshold_dsv"],
        )
        hits = misses = false_alarms = correct_neg = 0
        for ed in event_data:
            result = score_cell(ed["rh_days"], ed["temp_days"], model)
            predicted_red = band(result.risk) == "red"
            label = ed["label"]
            if label == 1 and predicted_red:
                hits += 1
            elif label == 1 and not predicted_red:
                misses += 1
            elif label == 0 and predicted_red:
                false_alarms += 1
            else:
                correct_neg += 1
        pod = hits / (hits + misses) if (hits + misses) else 0.0
        far = false_alarms / (hits + false_alarms) if (hits + false_alarms) else 0.0
        csi = hits / (hits + misses + false_alarms) if (hits + misses + false_alarms) else 0.0
        cost = false_alarms * COST_FALSE_ALARM + misses * COST_MISS
        rows.append({
            "min_wet_hours": params["min_wet_hours"],
            "min_temp_c": params["min_temp_c"],
            "consecutive_days": params["consecutive_days"],
            "spray_threshold_dsv": params["spray_threshold_dsv"],
            "hits": hits, "misses": misses,
            "false_alarms": false_alarms, "correct_negatives": correct_neg,
            "pod": round(pod, 4), "far": round(far, 4), "csi": round(csi, 4),
            "total_cost": cost,
        })
        if i % 24 == 0 or i == len(combos):
            print("  [%3d/%d] tested" % (i, len(combos)))

    rows.sort(key=lambda r: r["total_cost"])

    print()
    print("=" * 80)
    print("TOP 10 BY TOTAL COST (ascending)")
    print("=" * 80)
    hdr = "%5s %5s %4s %3s | %4s %4s %3s %3s | %5s %5s %5s | %8s" % (
        "wet_h", "tmin", "conv", "dsv", "hits", "miss", "fa", "cn",
        "POD", "FAR", "CSI", "COST")
    print(hdr)
    print("-" * 80)
    for r in rows[:10]:
        print("%5d %5d %4d %3d | %4d %4d %3d %3d | %5.3f %5.3f %5.3f | Rs.%7d" % (
            r["min_wet_hours"], r["min_temp_c"], r["consecutive_days"],
            r["spray_threshold_dsv"], r["hits"], r["misses"],
            r["false_alarms"], r["correct_negatives"],
            r["pod"], r["far"], r["csi"], r["total_cost"]))
    print("=" * 80)

    fieldnames = [
        "min_wet_hours", "min_temp_c", "consecutive_days", "spray_threshold_dsv",
        "hits", "misses", "false_alarms", "correct_negatives",
        "pod", "far", "csi", "total_cost",
    ]
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print()
    print("Wrote %s (%d rows)" % (OUTPUT_PATH, len(rows)))


if __name__ == "__main__":
    main()
