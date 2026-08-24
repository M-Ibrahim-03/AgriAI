"""Tests for engine/spray_window.py — pure spray window optimiser."""

from engine.spray_window import (
    find_spray_windows,
    best_window_before_risk,
    describe_window,
    SprayWindow,
)


# ── find_spray_windows ──────────────────────────────────────────────

def test_alldry_calm_mild_finds_window():
    n = 72
    windows = find_spray_windows([0.0] * n, [5.0] * n, [20.0] * n)
    assert len(windows) >= 1
    assert 0.0 < windows[0].quality <= 1.0


def test_constant_rain_empty():
    n = 72
    windows = find_spray_windows([1.0] * n, [5.0] * n, [20.0] * n)
    assert windows == []


def test_rain_after_rejects_window():
    """Rain 1 hour after a dry window must reject it (drying period check)."""
    n = 20
    precip = [0.0] * n
    precip[2] = 1.0
    windows = find_spray_windows(precip, [5.0] * n, [20.0] * n)
    assert not any(w.start_index == 0 for w in windows)


def test_high_wind_rejected():
    n = 72
    windows = find_spray_windows([0.0] * n, [20.0] * n, [20.0] * n)
    assert windows == []


def test_preferred_hour_scores_higher():
    """A 6 AM window scores higher than an identical 2 PM window."""
    n = 20
    precip = [0.0] * n
    for i in range(6):
        precip[i] = 1.0
    precip[10] = 1.0
    precip[13] = 1.0
    precip[18] = 1.0
    precip[19] = 1.0
    wind = [14.0] * n
    temp = [20.0] * n
    windows = find_spray_windows(precip, wind, temp)
    assert len(windows) >= 2
    q_morning = next(w.quality for w in windows if w.start_index == 6)
    q_afternoon = next(w.quality for w in windows if w.start_index == 14)
    assert q_morning > q_afternoon


# ── best_window_before_risk ─────────────────────────────────────────

def test_best_window_ontime():
    w1 = SprayWindow(6, 8, 0.9, "dry", None)
    w2 = SprayWindow(20, 22, 0.7, "dry", None)
    assert best_window_before_risk([w1, w2], 10) is w1


def test_best_window_late_fallback():
    w1 = SprayWindow(10, 12, 0.9, "dry, mild", None)
    w2 = SprayWindow(20, 22, 0.7, "dry, cool", None)
    result = best_window_before_risk([w1, w2], 8)
    assert result is not None
    assert result.reason.startswith("LATE:")
    assert result.quality == 0.9


def test_best_window_empty():
    assert best_window_before_risk([], 10) is None


# ── describe_window ─────────────────────────────────────────────────

def test_describe_window():
    w = SprayWindow(30, 33, 0.95, "dry, light wind, mild, morning", None)
    labels = ["Monday", "Tuesday", "Wednesday"]
    assert describe_window(w, labels) == (
        "Tuesday 6 AM to 9 AM - dry, light wind, mild, morning"
    )
