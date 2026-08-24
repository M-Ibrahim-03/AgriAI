"""Adapters layer — network I/O and caching for weather data."""

from __future__ import annotations

import json
from pathlib import Path

import requests

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
REQUEST_TIMEOUT = 30


def build_node_lattice(
    min_lat: float, max_lat: float,
    min_lon: float, max_lon: float,
    step: float = 0.1,
) -> list[tuple[float, float]]:
    """Return a regular grid of (lat, lon) covering the bounding box."""
    if min_lat > max_lat:
        raise ValueError(
            f"min_lat ({min_lat}) must be <= max_lat ({max_lat})"
        )
    if min_lon > max_lon:
        raise ValueError(
            f"min_lon ({min_lon}) must be <= max_lon ({max_lon})"
        )
    nodes: list[tuple[float, float]] = []
    lat = min_lat
    while lat <= max_lat + step / 2:
        lon = min_lon
        while lon <= max_lon + step / 2:
            nodes.append((round(lat, 6), round(lon, 6)))
            lon += step
        lat += step
    return nodes


def fetch_nodes(
    nodes: list[tuple[float, float]],
    past_days: int = 7,
) -> dict[tuple[float, float], dict]:
    """Fetch hourly RH and temp for every node in one Open-Meteo call."""
    if not nodes:
        return {}

    lats = ",".join(str(n) for n, _ in nodes)
    lons = ",".join(str(n) for _, n in nodes)

    params = {
        "latitude": lats,
        "longitude": lons,
        "hourly": "relative_humidity_2m,temperature_2m",
        "past_days": past_days,
        "forecast_days": 7,
        "timezone": "auto",
    }

    resp = requests.get(OPEN_METEO_URL, params=params, timeout=REQUEST_TIMEOUT)
    if resp.status_code != 200:
        raise RuntimeError(
            f"Open-Meteo returned HTTP {resp.status_code}: {resp.text[:200]}"
        )

    body = resp.json()

    # Single-node response is a dict; multi-node is a list.
    results = body if isinstance(body, list) else [body]

    out: dict[tuple[float, float], dict] = {}
    for node, result in zip(nodes, results):
        hourly = result.get("hourly", {})
        out[node] = {
            "rh": hourly.get("relative_humidity_2m", []),
            "temp": hourly.get("temperature_2m", []),
            "time": hourly.get("time", []),
        }

    return out


def save_cache(data: dict, path: str) -> None:
    """Persist the node dict as JSON (keys become 'lat,lon' strings)."""
    serialisable = {
        f"{lat},{lon}": payload for (lat, lon), payload in data.items()
    }
    Path(path).write_text(json.dumps(serialisable, indent=2))


def load_cache(path: str) -> dict[tuple[float, float], dict]:
    """Load a previously-saved JSON cache back into a (lat,lon)-keyed dict."""
    raw: dict[str, dict] = json.loads(Path(path).read_text())
    out: dict[tuple[float, float], dict] = {}
    for key, payload in raw.items():
        lat_s, lon_s = key.split(",")
        out[(float(lat_s), float(lon_s))] = payload
    return out
