"""Tests for engine/interpolate.py – pure interpolation functions."""

from engine.interpolate import bilinear, temp_with_lapse, interpolation_confidence, surrounding_values


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



# -- interpolation_confidence -------------------------------------------

def test_interpolation_confidence_identical_values():
    assert interpolation_confidence([10.0, 10.0, 10.0, 10.0]) == 1.0


def test_interpolation_confidence_spread_at_25pct():
    # mean=10, spread=2.5 -> ratio=0.25 -> confidence=0.0
    assert interpolation_confidence([8.75, 11.25]) == 0.0


def test_interpolation_confidence_empty():
    assert interpolation_confidence([]) == 0.0


def test_interpolation_confidence_single_node():
    assert interpolation_confidence([42.0]) == 1.0


def test_interpolation_confidence_zero_mean():
    assert interpolation_confidence([0.0, 0.0]) == 1.0
    assert interpolation_confidence([-1.0, 1.0]) == 0.0


# -- surrounding_values ------------------------------------------------

def test_surrounding_values_returns_four_nodes():
    nodes = {
        (10.0, 20.0): {"rh": [80.0], "temp": [20.0]},
        (10.0, 20.1): {"rh": [81.0], "temp": [21.0]},
        (10.1, 20.0): {"rh": [82.0], "temp": [22.0]},
        (10.1, 20.1): {"rh": [83.0], "temp": [23.0]},
    }
    vals = surrounding_values(10.05, 20.05, nodes, "rh")
    assert len(vals) == 4
    assert sorted(v[0] for v in vals) == [80.0, 81.0, 82.0, 83.0]


def test_surrounding_values_empty_nodes():
    assert surrounding_values(10.0, 20.0, {}, "rh") == []
