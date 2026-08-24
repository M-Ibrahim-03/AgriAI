"""PRAHARI cell-level disease-risk scorer."""

from __future__ import annotations

from dataclasses import dataclass

from engine.rules import (
    accumulate_dsv,
    criterion_met,
    daily_min_temp,
    hours_rh_at_or_above,
    mean_temp_during_wet_spell,
    qualifies_day,
    wallin_dsv,
)


@dataclass(frozen=True)
class DiseaseModel:
    name: str
    rh_threshold: float = 90.0
    min_wet_hours: int = 6        # Hutton
    min_temp_c: float = 10.0
    consecutive_days: int = 2
    spray_threshold_dsv: int = 18


@dataclass(frozen=True)
class CellRisk:
    risk: float          # 0.0 to 1.0
    accumulated_dsv: int
    criterion_alert: bool
    reason: str          # short plain-English explanation
    confidence: float = 1.0
    confidence_label: str = "high"


def _build_reason(
    model: DiseaseModel,
    day_flags: list[bool],
    criterion_alert: bool,
    wet_hours_seen: list[int],
    min_temp_seen: list[float],
) -> str:
    if not day_flags:
        return "No data."

    run = 0
    max_run = 0
    for f in day_flags:
        run = run + 1 if f else 0
        max_run = max(max_run, run)

    avg_wet = (
        round(sum(h for h, f in zip(wet_hours_seen, day_flags) if f) / max(sum(day_flags), 1))
        if any(day_flags)
        else 0
    )
    warmest = max((t for t, f in zip(min_temp_seen, day_flags) if f), default=0.0)

    if criterion_alert:
        return (
            f"{model.consecutive_days} back-to-back days with "
            f"{avg_wet}h of humidity above {model.rh_threshold:.0f}% "
            f"and min temp {warmest:.0f}C"
        )
    return (
        f"{sum(day_flags)}/{len(day_flags)} days qualify; "
        f"no {model.consecutive_days}-day streak yet"
    )


def score_cell(
    hourly_rh_by_day: list[list[float]],
    hourly_temp_by_day: list[list[float]],
    model: DiseaseModel,
    *,
    confidence: float = 1.0,
) -> CellRisk:
    """Return a risk score for one grid cell over a multi-day window."""
    day_flags: list[bool] = []
    wet_hours_seen: list[int] = []
    min_temp_seen: list[float] = []
    daily_dsv: list[int] = []

    for rh_day, temp_day in zip(hourly_rh_by_day, hourly_temp_by_day):
        wet = hours_rh_at_or_above(rh_day, model.rh_threshold)
        wet_hours_seen.append(wet)
        min_temp_seen.append(daily_min_temp(temp_day))
        day_flags.append(
            qualifies_day(rh_day, temp_day,
                          rh=model.rh_threshold,
                          hours=model.min_wet_hours,
                          tmin=model.min_temp_c)
        )
        mwt = mean_temp_during_wet_spell(temp_day, rh_day, model.rh_threshold)
        daily_dsv.append(wallin_dsv(mwt, wet))

    alert = criterion_met(day_flags, model.consecutive_days)
    accumulated = accumulate_dsv(daily_dsv)

    risk = min(1.0, accumulated / model.spray_threshold_dsv)
    if alert:
        risk = max(risk, 0.75)

    reason = _build_reason(model, day_flags, alert, wet_hours_seen, min_temp_seen)

    if confidence >= 0.7:
        conf_label = "high"
    elif confidence >= 0.4:
        conf_label = "medium"
    else:
        conf_label = "low"

    return CellRisk(
        risk=risk,
        accumulated_dsv=accumulated,
        criterion_alert=alert,
        reason=reason,
        confidence=confidence,
        confidence_label=conf_label,
    )


def band(risk: float, amber: float = 0.45, red: float = 0.75) -> str:
    """Map a 0-1 risk score to a green/amber/red band."""
    if risk >= red:
        return "red"
    if risk >= amber:
        return "amber"
    return "green"

