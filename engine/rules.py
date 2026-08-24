"""PRAHARI crop-disease forecast engine – pure mathematical rules."""

WALLIN_DEFAULT = [
    (7.2,  11.6, [(15,0), (18,1), (21,2), (24,3)]),
    (11.7, 15.0, [(12,0), (15,1), (18,2), (21,3), (24,4)]),
    (15.1, 26.6, [(9,0),  (12,1), (15,2), (18,3), (24,4)]),
]
# (temp_low, temp_high, [(min_wet_hours_for_this_dsv, dsv), ...])


def hours_rh_at_or_above(hourly_rh: list[float], threshold: float = 90.0) -> int:
    """Count hours where relative humidity is at or above threshold (inclusive)."""
    return sum(1 for rh in hourly_rh if rh >= threshold)


def daily_min_temp(hourly_temp: list[float]) -> float:
    """Return the daily minimum temperature, or float('inf') for empty input."""
    return min(hourly_temp) if hourly_temp else float("inf")


def mean_temp_during_wet_spell(
    hourly_temp: list[float], hourly_rh: list[float], threshold: float = 90.0
) -> float | None:
    """Mean temperature during hours where RH >= threshold; None if no wet hours."""
    wet = [t for t, rh in zip(hourly_temp, hourly_rh) if rh >= threshold]
    return sum(wet) / len(wet) if wet else None


def qualifies_day(
    hourly_rh: list[float],
    hourly_temp: list[float],
    *,
    rh: float = 90.0,
    hours: int = 6,
    tmin: float = 10.0,
) -> bool:
    """True when min temp >= tmin AND hours with RH >= rh >= hours."""
    return daily_min_temp(hourly_temp) >= tmin and hours_rh_at_or_above(hourly_rh, rh) >= hours


def criterion_met(day_flags: list[bool], consecutive: int = 2) -> bool:
    """True only if a run of *consecutive* consecutive True values exists."""
    count = 0
    for flag in day_flags:
        count = count + 1 if flag else 0
        if count >= consecutive:
            return True
    return False


def wallin_dsv(
    mean_wet_temp: float | None, wet_hours: int, table: list = WALLIN_DEFAULT
) -> int:
    """Return the Wallin DSV for given mean wet-bulb temperature and wet hours."""
    if mean_wet_temp is None:
        return 0
    for temp_low, temp_high, thresholds in table:
        if temp_low <= mean_wet_temp <= temp_high:
            for hrs, dsv in thresholds:
                if wet_hours < hrs:
                    return dsv
            return thresholds[-1][1]
    return 0


def accumulate_dsv(daily_dsv: list[int], window: int = 7) -> int:
    """Sum of the last *window* daily DSV values."""
    return sum(daily_dsv[-window:])
