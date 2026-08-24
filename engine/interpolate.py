"""PRAHARI interpolation – pure spatial estimation from lattice nodes."""

from __future__ import annotations

import math


def bilinear(
    target_lat: float,
    target_lon: float,
    nodes: dict[tuple[float, float], dict],
) -> dict[str, list[float]]:
    """Estimate hourly 'rh' and 'temp' at a point via inverse-distance weighting
    from the 4 surrounding lattice nodes."""
    if not nodes:
        return {"rh": [], "temp": []}

    lats = sorted({lat for lat, _ in nodes})
    lons = sorted({lon for _, lon in nodes})

    def _bracket(vals: list[float], target: float) -> tuple[float, float]:
        for i, v in enumerate(vals):
            if v >= target:
                lo = vals[i - 1] if i > 0 else v
                return lo, v
        return vals[-1], vals[-1]

    lat_lo, lat_hi = _bracket(lats, target_lat)
    lon_lo, lon_hi = _bracket(lons, target_lon)

    corners = [
        (lat_lo, lon_lo),
        (lat_lo, lon_hi),
        (lat_hi, lon_lo),
        (lat_hi, lon_hi),
    ]

    weights = []
    for corner in corners:
        d = math.hypot(target_lat - corner[0], target_lon - corner[1])
        weights.append(1.0 / max(d, 1e-12))

    total_w = sum(weights)

    sample = nodes[corners[0]]
    n_hours = len(sample.get("rh", []))

    result_rh = [0.0] * n_hours
    result_temp = [0.0] * n_hours

    for w, corner in zip(weights, corners):
        node_data = nodes[corner]
        rh_arr = node_data.get("rh", [])
        temp_arr = node_data.get("temp", [])
        for i in range(n_hours):
            result_rh[i] += w * (rh_arr[i] if i < len(rh_arr) else 0.0)
            result_temp[i] += w * (temp_arr[i] if i < len(temp_arr) else 0.0)

    for i in range(n_hours):
        result_rh[i] /= total_w
        result_temp[i] /= total_w

    return {"rh": result_rh, "temp": result_temp}


def temp_with_lapse(
    temp_c: float,
    node_elev_m: float,
    cell_elev_m: float,
    lapse_c_per_km: float = 6.5,
) -> float:
    """Adjust temperature for altitude difference using a standard lapse rate.
    Never apply lapse correction to humidity – RH does not follow a lapse rate."""
    return temp_c + (node_elev_m - cell_elev_m) / 1000.0 * lapse_c_per_km
