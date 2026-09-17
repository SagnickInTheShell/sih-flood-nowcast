"""Deterministic synthetic reference ward for guaranteed offline demoing.

This is NOT a real place. The anchor coordinate (12.9716N, 77.5946E by
default) is a `placeholder_anchor` used only so the generated ward has
valid lat/lng for the map to render -- the UI must label this ward
"Synthetic Reference Ward", never claim it is a real location.

Switch to PILOT_MODE=real and configure REAL_WARD_BBOX to ingest an
actual location via OpenStreetMap + SRTM (see real_ward.py and
scripts/download_srtm.py).

Everything here is derived from SYNTHETIC_SEED so every run, and every
teammate's machine, produces byte-identical output.
"""
from __future__ import annotations

import math
from functools import lru_cache

import networkx as nx
import numpy as np
from scipy.ndimage import zoom

from app.core.config import settings
from app.gis.ward_provider import CriticalInfra, WardDataProvider

METERS_PER_DEG_LAT = 111_320.0


def _meters_per_deg_lng(lat_deg: float) -> float:
    return METERS_PER_DEG_LAT * math.cos(math.radians(lat_deg))


def _fractal_noise(n: int, seed: int, octaves: int = 4, persistence: float = 0.5) -> np.ndarray:
    """Deterministic value noise (sum of upsampled random octaves).

    Standalone stand-in for simplex noise so we don't need an extra
    third-party noise library just for this one effect.
    """
    rng = np.random.RandomState(seed)
    total = np.zeros((n, n))
    amplitude = 1.0
    max_amp = 0.0
    freq_cells = 4
    for _ in range(octaves):
        coarse = rng.uniform(-1, 1, size=(freq_cells, freq_cells))
        upsampled = zoom(coarse, n / freq_cells, order=3)
        upsampled = upsampled[:n, :n]
        total += amplitude * upsampled
        max_amp += amplitude
        amplitude *= persistence
        freq_cells *= 2
    total /= max_amp
    return total


def _point_segment_distance(rows: np.ndarray, cols: np.ndarray, p0, p1) -> np.ndarray:
    """Vectorized perpendicular distance from grid points to a segment."""
    r0, c0 = p0
    r1, c1 = p1
    seg = np.array([r1 - r0, c1 - c0], dtype=float)
    seg_len2 = float(seg @ seg)
    pr = rows - r0
    pc = cols - c0
    t = (pr * seg[0] + pc * seg[1]) / seg_len2
    t = np.clip(t, 0.0, 1.0)
    proj_r = r0 + t * seg[0]
    proj_c = c0 + t * seg[1]
    return np.sqrt((rows - proj_r) ** 2 + (cols - proj_c) ** 2)


class SyntheticWardProvider(WardDataProvider):
    is_synthetic = True

    def __init__(self):
        self.seed = settings.SYNTHETIC_SEED
        self.n = settings.GRID_SIZE_CELLS
        self.resolution_m = settings.GRID_RESOLUTION_M
        self.anchor_lat = settings.ANCHOR_LAT
        self.anchor_lng = settings.ANCHOR_LNG
        # Depression centreline: roughly NE -> SW through the middle,
        # in (row, col) grid-cell space. row 0 = north edge, col 0 = west edge.
        self.depression_p0 = (12.0, 88.0)  # near NE
        self.depression_p1 = (88.0, 12.0)  # near SW

    # ---- geometry -----------------------------------------------------

    def grid_resolution_m(self) -> float:
        return self.resolution_m

    def cell_to_latlng(self, row: float, col: float) -> tuple[float, float]:
        dlat = -(row * self.resolution_m) / METERS_PER_DEG_LAT
        dlng = (col * self.resolution_m) / _meters_per_deg_lng(self.anchor_lat)
        return (self.anchor_lat + dlat, self.anchor_lng + dlng)

    # ---- elevation ------------------------------------------------------

    @lru_cache(maxsize=1)
    def _elevation(self) -> np.ndarray:
        n = self.n
        rows, cols = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
        # Base slope: 45m (NW, row0/col0) -> 38m (SE, row n/col n)
        t = (rows + cols) / (2 * (n - 1))
        base = 45.0 - 7.0 * t
        noise = 1.5 * _fractal_noise(n, seed=self.seed)
        dist_to_depression = _point_segment_distance(
            rows.astype(float), cols.astype(float),
            self.depression_p0, self.depression_p1,
        )
        sigma = 4.0  # cells (~80m) half-width of the carved channel
        depression = -2.0 * np.exp(-0.5 * (dist_to_depression / sigma) ** 2)
        return base + noise + depression

    def get_elevation_grid(self) -> np.ndarray:
        return self._elevation()

    # ---- curve number / land use ----------------------------------------

    @lru_cache(maxsize=1)
    def _curve_number(self) -> np.ndarray:
        n = self.n
        rows, cols = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
        rows_f, cols_f = rows.astype(float), cols.astype(float)
        cn = np.full((n, n), 75.0)  # residential default

        # Two diagonal arterials -> commercial/paved corridor (CN=90)
        arterial_a = _point_segment_distance(rows_f, cols_f, (0, 0), (n - 1, n - 1))
        arterial_b = _point_segment_distance(rows_f, cols_f, (0, n - 1), (n - 1, 0))
        near_arterial = (arterial_a < 3.0) | (arterial_b < 3.0)
        cn[near_arterial] = 90.0

        # Green space / park hugging the drainage depression (CN=55)
        dist_to_depression = _point_segment_distance(
            rows_f, cols_f, self.depression_p0, self.depression_p1
        )
        near_depression = dist_to_depression < 6.0
        cn[near_depression] = 55.0  # takes priority over arterial tagging

        return cn

    def get_curve_number_grid(self) -> np.ndarray:
        return self._curve_number()

    # ---- road / drainage-tagged network ----------------------------------

    @lru_cache(maxsize=1)
    def _road_graph(self) -> nx.Graph:
        n = self.n
        grid_n = 8  # 8x8 orthogonal grid of roads
        rng = np.random.RandomState(self.seed)
        g = nx.Graph()

        def node_id(r, c):
            return f"n_{r}_{c}"

        def grid_rc(r, c):
            return (r * (n - 1) / (grid_n - 1), c * (n - 1) / (grid_n - 1))

        for r in range(grid_n):
            for c in range(grid_n):
                gr, gc = grid_rc(r, c)
                lat, lng = self.cell_to_latlng(gr, gc)
                g.add_node(node_id(r, c), lat=lat, lng=lng, grid_row=gr, grid_col=gc,
                           is_major_junction=False)

        def edge_length_m(a, b):
            (r1, c1) = g.nodes[a]["grid_row"], g.nodes[a]["grid_col"]
            (r2, c2) = g.nodes[b]["grid_row"], g.nodes[b]["grid_col"]
            return math.hypot(r2 - r1, c2 - c1) * self.resolution_m

        # Orthogonal grid roads, ~30% tagged as carrying a storm drain
        for r in range(grid_n):
            for c in range(grid_n):
                a = node_id(r, c)
                if c + 1 < grid_n:
                    b = node_id(r, c + 1)
                    has_drain = rng.uniform() < 0.30
                    g.add_edge(a, b, length_m=edge_length_m(a, b), is_arterial=False,
                               has_drain=has_drain, edge_id=f"r_{a}_{b}")
                if r + 1 < grid_n:
                    b = node_id(r + 1, c)
                    has_drain = rng.uniform() < 0.30
                    g.add_edge(a, b, length_m=edge_length_m(a, b), is_arterial=False,
                               has_drain=has_drain, edge_id=f"r_{a}_{b}")

        # 2 diagonal arterial roads crossing the grid, always drained
        for r in range(grid_n - 1):
            a, b = node_id(r, r), node_id(r + 1, r + 1)
            g.add_edge(a, b, length_m=edge_length_m(a, b), is_arterial=True,
                       has_drain=True, edge_id=f"r_{a}_{b}")
        for r in range(grid_n - 1):
            a, b = node_id(r, grid_n - 1 - r), node_id(r + 1, grid_n - 2 - r)
            g.add_edge(a, b, length_m=edge_length_m(a, b), is_arterial=True,
                       has_drain=True, edge_id=f"r_{a}_{b}")

        # 4 major drainage junctions: nearest road-grid node to 4 points
        # spaced along the depression centreline's lowest points.
        for t in (0.2, 0.4, 0.6, 0.8):
            target_r = self.depression_p0[0] + t * (self.depression_p1[0] - self.depression_p0[0])
            target_c = self.depression_p0[1] + t * (self.depression_p1[1] - self.depression_p0[1])
            best_node, best_d = None, math.inf
            for node, data in g.nodes(data=True):
                d = math.hypot(data["grid_row"] - target_r, data["grid_col"] - target_c)
                if d < best_d:
                    best_node, best_d = node, d
            g.nodes[best_node]["is_major_junction"] = True

        return g

    def get_road_graph(self) -> nx.Graph:
        return self._road_graph().copy()

    # ---- critical infrastructure ------------------------------------------

    @lru_cache(maxsize=1)
    def _critical_infra(self) -> tuple[CriticalInfra, ...]:
        # Fixed, clearly-labelled placements within the grid.
        points = [
            ("hospital_01", "hospital", "Ward Alpha General Hospital", 15, 82),
            ("fire_station_01", "fire_station", "Ward Alpha Fire Station", 50, 50),
            ("shelter_01", "shelter", "Ward Alpha Community Shelter", 85, 20),
        ]
        out = []
        for infra_id, infra_type, name, row, col in points:
            lat, lng = self.cell_to_latlng(row, col)
            out.append(CriticalInfra(infra_id, infra_type, name, lat, lng))
        return tuple(out)

    def get_critical_infrastructure(self) -> list[CriticalInfra]:
        return list(self._critical_infra())
