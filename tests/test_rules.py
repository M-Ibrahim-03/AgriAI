"""Tests for engine/rules.py — pure function behaviour."""

from engine.rules import (
    hours_rh_at_or_above,
    daily_min_temp,
    mean_temp_during_wet_spell,
    qualifies_day,
    criterion_met,
    wallin_dsv,
    accumulate_dsv,
    WALLIN_DEFAULT,
)


# ── hours_rh_at_or_above ────────────────────────────────────────────

def test_hours_rh_at_or_above_inclusive_boundary():
    assert hours_rh_at_or_above([90.0, 90.0, 89.9]) == 2


def test_hours_rh_at_or_above_empty():
    assert hours_rh_at_or_above([]) == 0


def test_hours_rh_at_or_above_all_90():
    assert hours_rh_at_or_above([90.0, 90.0, 90.0]) == 3


def test_hours_rh_at_or_above_custom_threshold():
    assert hours_rh_at_or_above([80.0, 85.0, 95.0], threshold=85.0) == 2


# ── daily_min_temp ──────────────────────────────────────────────────

def test_daily_min_temp_basic():
    assert daily_min_temp([10, 20, 30, 5, 15]) == 5


def test_daily_min_temp_empty():
    assert daily_min_temp([]) == float("inf")


def test_daily_min_temp_single_value():
    assert daily_min_temp([42.0]) == 42.0


# ── mean_temp_during_wet_spell ──────────────────────────────────────

def test_mean_temp_during_wet_spell_basic():
    assert mean_temp_during_wet_spell([10, 20, 30], [95, 95, 50]) == 15.0


def test_mean_temp_during_wet_spell_no_wet_hours():
    assert mean_temp_during_wet_spell([10, 20, 30], [50, 50, 50]) is None


def test_mean_temp_during_wet_spell_empty():
    assert mean_temp_during_wet_spell([], []) is None


def test_mean_temp_during_wet_spell_all_wet():
    assert mean_temp_during_wet_spell([10, 20, 30], [90, 91, 92]) == 20.0


def test_mean_temp_during_wet_spell_boundary_90():
    assert mean_temp_during_wet_spell([10, 20, 30], [90, 89, 90]) == 20.0


# ── qualifies_day ───────────────────────────────────────────────────

def test_qualifies_day_passes():
    assert qualifies_day([95.0] * 12, [15.0] * 24) is True


def test_qualifies_day_insufficient_hours():
    assert qualifies_day([95.0] * 5, [15.0] * 24) is False


def test_qualifies_day_below_tmin():
    assert qualifies_day([95.0] * 12, [5.0] * 24) is False


def test_qualifies_day_empty():
    assert qualifies_day([], []) is False


def test_qualifies_day_boundary_temp():
    assert qualifies_day([95.0] * 12, [10.0] * 24) is True


def test_qualifies_day_just_below_boundary_temp():
    assert qualifies_day([95.0] * 12, [9.9] * 24) is False


# ── criterion_met ───────────────────────────────────────────────────

def test_criterion_met_alternating_false():
    assert criterion_met([True, False, True]) is False


def test_criterion_met_consecutive_pair():
    assert criterion_met([True, True, False]) is True


def test_criterion_met_interleaved_false():
    assert criterion_met([True, False, True, False, True]) is False


def test_criterion_met_empty():
    assert criterion_met([]) is False


def test_criterion_met_single_true():
    assert criterion_met([True]) is False


def test_criterion_met_three_consecutive():
    assert criterion_met([True, True, True], consecutive=3) is True


def test_criterion_met_all_false():
    assert criterion_met([False, False, False]) is False


# ── wallin_dsv ──────────────────────────────────────────────────────

def test_wallin_dsv_meets_threshold():
    assert wallin_dsv(20.0, 10) == 1


def test_wallin_dsv_below_threshold():
    assert wallin_dsv(20.0, 8) == 0


def test_wallin_dsv_none_temp():
    assert wallin_dsv(None, 20) == 0


def test_wallin_dsv_outside_bands():
    assert wallin_dsv(5.0, 24) == 0


def test_wallin_dsv_all_thresholds_met():
    assert wallin_dsv(20.0, 24) == 4


def test_wallin_dsv_boundary_temp_low():
    assert wallin_dsv(7.2, 14) == 0
    assert wallin_dsv(7.2, 15) == 1


def test_wallin_dsv_boundary_temp_high():
    assert wallin_dsv(26.6, 24) == 4


def test_wallin_dsv_custom_table():
    custom = [(10.0, 20.0, [(5, 0), (10, 1)])]
    assert wallin_dsv(15.0, 7, table=custom) == 1
    assert wallin_dsv(15.0, 3, table=custom) == 0


# ── accumulate_dsv ──────────────────────────────────────────────────

def test_accumulate_dsv_basic():
    assert accumulate_dsv([1, 2, 3, 4, 5, 6, 7]) == 28


def test_accumulate_dsv_short_list():
    assert accumulate_dsv([1, 2], window=7) == 3


def test_accumulate_dsv_empty():
    assert accumulate_dsv([]) == 0


def test_accumulate_dsv_custom_window():
    assert accumulate_dsv([1, 1, 1, 1, 1], window=3) == 3
