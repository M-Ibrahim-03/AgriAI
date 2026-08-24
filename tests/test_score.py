"""Tests for engine/score.py — scorer and band logic."""

from engine.score import DiseaseModel, CellRisk, score_cell, band


# ── helpers ──────────────────────────────────────────────────────────

COLD_DRY_MODEL = DiseaseModel(name="cold-dry")
WET_MILD_MODEL = DiseaseModel(name="wet-mild")


def _cold_dry_day() -> tuple[list[float], list[float]]:
    """3 days of 50% RH and 5°C — nothing qualifies."""
    rh = [50.0] * 24
    temp = [5.0] * 24
    return rh, temp


def _wet_mild_day() -> tuple[list[float], list[float]]:
    """1 day of 95% RH and 18°C — fully qualifying."""
    rh = [95.0] * 24
    temp = [18.0] * 24
    return rh, temp


# ── score_cell: safe case ────────────────────────────────────────────

def test_cold_dry_green():
    days = [_cold_dry_day() for _ in range(3)]
    rh_by_day = [d[0] for d in days]
    temp_by_day = [d[1] for d in days]

    result = score_cell(rh_by_day, temp_by_day, COLD_DRY_MODEL)

    assert result.risk == 0.0
    assert result.accumulated_dsv == 0
    assert result.criterion_alert is False
    assert band(result.risk) == "green"


# ── score_cell: dangerous case ───────────────────────────────────────

def test_wet_mild_red():
    days = [_wet_mild_day() for _ in range(7)]
    rh_by_day = [d[0] for d in days]
    temp_by_day = [d[1] for d in days]

    result = score_cell(rh_by_day, temp_by_day, WET_MILD_MODEL)

    assert result.risk == 1.0
    assert result.accumulated_dsv == 28
    assert result.criterion_alert is True
    assert band(result.risk) == "red"


# ── band ─────────────────────────────────────────────────────────────

def test_band_green():
    assert band(0.0) == "green"
    assert band(0.44) == "green"


def test_band_amber():
    assert band(0.45) == "amber"
    assert band(0.74) == "amber"


def test_band_red():
    assert band(0.75) == "red"
    assert band(1.0) == "red"


# ── empty input ──────────────────────────────────────────────────────

def test_score_cell_empty():
    result = score_cell([], [], COLD_DRY_MODEL)
    assert result.risk == 0.0
    assert result.criterion_alert is False
    assert band(result.risk) == "green"



# -- confidence --------------------------------------------------------

def test_score_cell_default_confidence():
    days = [_cold_dry_day() for _ in range(3)]
    result = score_cell([d[0] for d in days], [d[1] for d in days], COLD_DRY_MODEL)
    assert result.confidence == 1.0
    assert result.confidence_label == "high"


def test_score_cell_low_confidence():
    days = [_cold_dry_day() for _ in range(3)]
    result = score_cell(
        [d[0] for d in days], [d[1] for d in days], COLD_DRY_MODEL,
        confidence=0.2,
    )
    assert result.confidence == 0.2
    assert result.confidence_label == "low"


def test_score_cell_medium_confidence():
    days = [_cold_dry_day() for _ in range(3)]
    result = score_cell(
        [d[0] for d in days], [d[1] for d in days], COLD_DRY_MODEL,
        confidence=0.5,
    )
    assert result.confidence == 0.5
    assert result.confidence_label == "medium"
