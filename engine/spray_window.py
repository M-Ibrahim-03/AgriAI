"""Spray-window optimiser — pure functions, no I/O."""

from __future__ import annotations

from dataclasses import dataclass

SPRAY_RULES: dict = {
    "dry_hours_needed_after": 2,
    "max_rain_mm_in_window": 0.1,
    "max_wind_kmh": 15.0,
    "min_temp_c": 8.0,
    "max_temp_c": 32.0,
    "preferred_hours": [6, 7, 8, 9, 17, 18],
    "min_window_hours": 2,
}


@dataclass(frozen=True)
class SprayWindow:
    start_index: int
    end_index: int
    quality: float
    reason: str
    blocked_by: str | None


def _fmt_hour(h: int) -> str:
    if h == 0:
        return "12 AM"
    if h < 12:
        return f"{h} AM"
    if h == 12:
        return "12 PM"
    return f"{h - 12} PM"


def find_spray_windows(
    hourly_precip: list[float],
    hourly_wind: list[float],
    hourly_temp: list[float],
    hourly_is_daylight: list[bool] | None = None,
    rules: dict = SPRAY_RULES,
    horizon_hours: int = 72,
) -> list[SprayWindow]:
    """Slide a window across hourly data and return valid spray windows sorted by quality."""
    dry_after: int = rules["dry_hours_needed_after"]
    max_rain: float = rules["max_rain_mm_in_window"]
    max_wind: float = rules["max_wind_kmh"]
    min_temp: float = rules["min_temp_c"]
    max_temp: float = rules["max_temp_c"]
    preferred: set[int] = set(rules["preferred_hours"])
    win_len: int = rules["min_window_hours"]

    n = min(horizon_hours, len(hourly_precip))
    valid: list[tuple[int, float, str]] = []

    for start in range(n - win_len + 1):
        end = start + win_len

        # --- validity checks (reject = continue) ---

        # Rain inside window
        rain_in = sum(hourly_precip[start:end])
        if rain_in > max_rain:
            continue

        # Drying period after window
        dry_end = min(end + dry_after, len(hourly_precip))
        rain_after = sum(hourly_precip[end:dry_end])
        if rain_after > max_rain:
            continue

        # Wind inside window
        wind_max = max(hourly_wind[start:end])
        if wind_max > max_wind:
            continue

        # Temperature inside window
        if any(
            hourly_temp[i] < min_temp or hourly_temp[i] > max_temp
            for i in range(start, end)
        ):
            continue

        # Daylight check
        if hourly_is_daylight is not None:
            if not all(hourly_is_daylight[start:end]):
                continue

        # --- quality score ---
        quality = 1.0
        if (start % 24) in preferred:
            quality *= 1.25
        quality *= 1 - (wind_max / max_wind) * 0.3
        extra_end = min(end + 6, len(hourly_precip))
        if sum(hourly_precip[end:extra_end]) <= max_rain:
            quality *= 1.15
        quality = min(quality, 1.0)

        # --- reason ---
        avg_temp = sum(hourly_temp[start:end]) / win_len
        parts = ["dry"]
        parts.append("light wind" if wind_max < 10 else "moderate wind")
        if avg_temp < 20:
            parts.append("cool")
        elif avg_temp < 28:
            parts.append("mild")
        else:
            parts.append("warm")
        parts.append("morning" if (start % 24) < 12 else "afternoon")
        reason = ", ".join(parts)

        valid.append((start, quality, reason))

    if not valid:
        return []

    # Merge overlapping valid windows into continuous runs
    runs: list[list[tuple[int, float, str]]] = []
    cur: list[tuple[int, float, str]] = [valid[0]]
    for i in range(1, len(valid)):
        prev_start = valid[i - 1][0]
        cur_start = valid[i][0]
        if cur_start <= prev_start + win_len - 1:
            cur.append(valid[i])
        else:
            runs.append(cur)
            cur = [valid[i]]
    runs.append(cur)

    windows: list[SprayWindow] = []
    for run in runs:
        merged_start = run[0][0]
        merged_end = run[-1][0] + win_len
        best = max(run, key=lambda x: x[1])
        windows.append(SprayWindow(
            start_index=merged_start,
            end_index=merged_end,
            quality=round(best[1], 4),
            reason=best[2],
            blocked_by=None,
        ))

    windows.sort(key=lambda w: w.quality, reverse=True)
    return windows


def best_window_before_risk(
    windows: list[SprayWindow],
    hours_until_risk: int,
) -> SprayWindow | None:
    """Highest-quality window ending at or before hours_until_risk; falls back to LATE."""
    if not windows:
        return None
    on_time = [w for w in windows if w.end_index <= hours_until_risk]
    if on_time:
        return max(on_time, key=lambda w: w.quality)
    best = max(windows, key=lambda w: w.quality)
    return SprayWindow(
        start_index=best.start_index,
        end_index=best.end_index,
        quality=best.quality,
        reason=f"LATE: {best.reason}",
        blocked_by=best.blocked_by,
    )


def describe_window(w: SprayWindow, day_labels: list[str]) -> str:
    """Human sentence like 'Tuesday 6 AM to 9 AM - dry, light wind, cool morning'."""
    day = day_labels[w.start_index // 24]
    start_h = _fmt_hour(w.start_index % 24)
    end_h = _fmt_hour(w.end_index % 24)
    return f"{day} {start_h} to {end_h} - {w.reason}"
