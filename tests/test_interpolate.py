"""Tests for engine/interpolate.py – pure interpolation functions."""

from engine.interpolate import bilinear, temp_with_lapse


def test_exact_node_returns_node_values():
    """A point exactly on a node should return that node's data."""
    nodes = {
        (10.0, 20.0): {"rh": [80.0, 85.0, 90.0], "temp": [22.0, 23.0, 24.0]},
        (10.0, 20.1): {"rh": [81.0, 86.0, 91.0], "temp": [22.1, 23.1, 24.1]},
        (10.1, 20.0): {"rh": [82.0, 87.0, 92.0], "temp": [22.2, 23.2, 24.2]},
        (10.1, 20.1): {"rh": [83.0, 88.0, 93.0], "temp": [22.3, 23.3, 24.3]},
    }
    result = bilinear(10.0, 20.0, nodes)
    assert result["rh"] == [80.0, 85.0, 90.0]
    assert result["temp"] == [22.0, 23.0, 24.0]


def test_midpoint_returns_average():
    """A point halfway between two nodes should return roughly their average."""
    nodes = {
        (10.0, 20.0): {"rh": [80.0], "temp": [20.0]},
        (10.0, 20.2): {"rh": [100.0], "temp": [30.0]},
        (10.1, 20.0): {"rh": [80.0], "temp": [20.0]},
        (10.1, 20.2): {"rh": [100.0], "temp": [30.0]},
    }
    result = bilinear(10.05, 20.1, nodes)
    assert abs(result["rh"][0] - 90.0) < 0.01
    assert abs(result["temp"][0] - 25.0) < 0.01


def test_temp_with_lapse_colder_at_higher_cell():
    """Cell higher than node should be warmer at cell."""
    node_elev = 200.0
    cell_elev = 1200.0
    temp_c = 20.0
    result = temp_with_lapse(temp_c, node_elev, cell_elev)
    # Node is cooler, so cell gets warmer: 20 + (-1000/1000)*6.5 = 13.5
    assert abs(result - 13.5) < 0.01


def test_temp_with_lapse_same_elevation():
    """Same elevation should return the original temperature."""
    assert temp_with_lapse(25.0, 500.0, 500.0) == 25.0
