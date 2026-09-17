"""SCS Curve Number rainfall-runoff method.

Source: USDA NRCS National Engineering Handbook, Part 630, Chapters 9-10.

    S  = (25400 / CN) - 254         potential maximum retention, mm
    Ia = IA_COEFFICIENT * S         initial abstraction
    Q  = (P - Ia)^2 / (P - Ia + S)  if P > Ia, else 0

IA_COEFFICIENT is the classic NEH-630 coefficient of 0.2. It is kept as a
named, swappable constant (not inlined) because later NEH-630 guidance
suggests 0.05 may better match observed data for many watersheds -- see
config.py's IA_COEFFICIENT setting.
"""
from __future__ import annotations

from app.core.config import settings


def potential_retention_mm(curve_number: float) -> float:
    if not (0 < curve_number <= 100):
        raise ValueError(f"curve_number must be in (0, 100], got {curve_number}")
    return (25400.0 / curve_number) - 254.0


def initial_abstraction_mm(s_mm: float, ia_coefficient: float | None = None) -> float:
    coeff = settings.IA_COEFFICIENT if ia_coefficient is None else ia_coefficient
    return coeff * s_mm


def runoff_mm(rainfall_mm: float, curve_number: float, ia_coefficient: float | None = None) -> float:
    """Runoff depth (mm) for a given storm rainfall depth and curve number."""
    s = potential_retention_mm(curve_number)
    ia = initial_abstraction_mm(s, ia_coefficient)
    if rainfall_mm <= ia:
        return 0.0
    return (rainfall_mm - ia) ** 2 / (rainfall_mm - ia + s)
