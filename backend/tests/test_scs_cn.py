"""Validates the SCS-CN formula against a worked example derived directly
from the formula (auditable, not a magic number).

Worked example: P = 100 mm, CN = 80
  S  = 25400/80 - 254 = 317.5 - 254 = 63.5
  Ia = 0.2 * 63.5 = 12.7
  Q  = (100 - 12.7)^2 / (100 - 12.7 + 63.5)
     = 87.3^2 / 150.8
     = 7621.29 / 150.8
     = 50.5384...
"""
import pytest

from app.hydrology.scs_cn import initial_abstraction_mm, potential_retention_mm, runoff_mm


def test_worked_example_p100_cn80():
    s = potential_retention_mm(80)
    assert s == pytest.approx(63.5)
    ia = initial_abstraction_mm(s, ia_coefficient=0.2)
    assert ia == pytest.approx(12.7)
    q = runoff_mm(100, 80, ia_coefficient=0.2)
    expected = (100 - 12.7) ** 2 / (100 - 12.7 + 63.5)
    assert q == pytest.approx(expected)
    assert q == pytest.approx(50.5384, rel=1e-3)


def test_no_runoff_below_initial_abstraction():
    assert runoff_mm(5, 60, ia_coefficient=0.2) == 0.0


def test_runoff_increases_with_rainfall():
    assert runoff_mm(80, 75) > runoff_mm(20, 75)


def test_runoff_increases_with_curve_number():
    assert runoff_mm(60, 90) > runoff_mm(60, 55)
