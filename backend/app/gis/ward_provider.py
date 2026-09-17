"""Abstract interface both the synthetic and real ward data sources satisfy.

This is the architectural seam required by §4 of the build spec: every
downstream stage (hydrology -> drainage graph -> GNN -> routing) is
written against this interface only, so switching PILOT_MODE from
"synthetic" to "real" requires zero changes anywhere else in the app.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import networkx as nx
import numpy as np


@dataclass(frozen=True)
class CriticalInfra:
    infra_id: str
    infra_type: str  # "hospital" | "fire_station" | "shelter"
    name: str
    lat: float
    lng: float


class WardDataProvider(ABC):
    """Everything downstream needs to know about a pilot ward."""

    is_synthetic: bool

    @abstractmethod
    def grid_resolution_m(self) -> float:
        """Metres per grid cell edge."""

    @abstractmethod
    def get_elevation_grid(self) -> np.ndarray:
        """(N, N) array of elevation in metres, row 0 = north edge."""

    @abstractmethod
    def get_curve_number_grid(self) -> np.ndarray:
        """(N, N) array of SCS curve numbers (30-98)."""

    @abstractmethod
    def cell_to_latlng(self, row: float, col: float) -> tuple[float, float]:
        """Georeference a (possibly fractional) grid cell to (lat, lng)."""

    @abstractmethod
    def get_road_graph(self) -> nx.Graph:
        """networkx.Graph. Nodes: {lat, lng}. Edges: {length_m, is_arterial,
        has_drain, is_major_junction (on adjacent nodes)}."""

    @abstractmethod
    def get_critical_infrastructure(self) -> list[CriticalInfra]:
        """Hospital(s), fire station(s), shelter(s) within the ward."""
