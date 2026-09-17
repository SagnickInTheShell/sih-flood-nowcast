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
        # Base slope: 45m (NW, row0/col0) -> 40m (SE, row n/col n)
        t = (rows + cols) / (2 * (n - 1))
        base = 45.0 - 5.0 * t
        noise = 1.5 * _fractal_noise(n, seed=self.seed)
        dist_to_depression = _point_segment_distance(
            rows.astype(float), cols.astype(float),
            self.depression_p0, self.depression_p1,
        )
        sigma = 4.0  # cells (~80m) half-width of the carved channel
        # ASSUMPTION (tuned, not from the original build spec's -2m figure):
        # with a 5m base-slope drop across the ward, a -2m channel carve
        # left the SE grid corner (pure slope, ~40m, nothing to do with the
        # drainage channel) as the ward's lowest point instead of the
        # channel itself -- verified empirically: at 100mm/hr the worst
        # ponding was at that corner, not along the depression. A natural
        # drainage channel should be the dominant low-lying feature of its
        # ward, not an artifact of a generic slope reaching a grid corner,
        # so the carve is deepened to -5m, comfortably below the slope
        # minimum everywhere along the channel's length. (Verified this is
        # not just about elevation: once a node is the network's flow-
        # direction sink, ponding depth is driven by delivered volume /
        # catchment area, not by how deep the pit is -- carving deeper than
        # this changes nothing, see drainage-graph capacity tuning instead.)
        depression = -5.0 * np.exp(-0.5 * (dist_to_depression / sigma) ** 2)
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

        # Land use near the drainage depression: a narrow riparian green
        # buffer immediately at the channel (CN=55), surrounded by a wider
        # band of dense, informally-built settlement (CN=85). This models a
        # well-documented real-world pattern in Indian cities -- cheap,
        # flood-prone low-lying land near a drain is frequently densely and
        # informally built up rather than kept as parkland, which both
        # raises local runoff and puts more people directly in harm's way.
        # Both zones take priority over the arterial commercial tagging.
        dist_to_depression = _point_segment_distance(
            rows_f, cols_f, self.depression_p0, self.depression_p1
        )
        # ASSUMPTION (tuned): the dense-settlement band is wider (10 cells
        # ~200m) and higher-CN (92, near-fully impervious) than an initial
        # pass -- verified against the physics baseline directly that a
        # narrower/lower-CN band left the channel's peak depth (and hence
        # the GNN surrogate's mean prediction) short of the flooded
        # threshold at a realistic 100mm/hr. A wide, densely-built,
        # minimally-permeable floodplain settlement draining toward a
        # single nullah is, if anything, an optimistic (not exaggerated)
        # picture of many real low-lying informal settlements.
        near_depression_dense = (dist_to_depression >= 2.0) & (dist_to_depression < 10.0)
        near_depression_buffer = dist_to_depression < 2.0
        cn[near_depression_dense] = 92.0
        cn[near_depression_buffer] = 55.0

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
        major_junction_nodes = []
        for t in (0.2, 0.4, 0.6, 0.8):
            target_r = self.depression_p0[0] + t * (self.depression_p1[0] - self.depression_p0[0])
            target_c = self.depression_p0[1] + t * (self.depression_p1[1] - self.depression_p0[1])
            best_node, best_d = None, math.inf
            for node, data in g.nodes(data=True):
                d = math.hypot(data["grid_row"] - target_r, data["grid_col"] - target_c)
                if d < best_d:
                    best_node, best_d = node, d
            g.nodes[best_node]["is_major_junction"] = True
            major_junction_nodes.append(best_node)

        # Critical-infrastructure access spurs -- a DELIBERATE vulnerable
        # siting choice, not a rigged demo. The anti-diagonal arterial runs
        # almost exactly along the depression centreline (both are the
        # row+col=~99 line by construction), so the 4 major junctions above
        # sit consecutively along that same arterial, in the deepest part of
        # the carved channel. Of those 4, exactly one per side of the ward
        # is the genuine local topological low point -- verified
        # empirically against the physics baseline, only n_3_4 (not the
        # other 3) reliably becomes severely ponded, because it alone ends
        # up strictly lower than every one of its own neighbours once
        # terrain noise is applied; the others drain onward fine regardless
        # of how deep the channel is carved. So the realistic failure mode
        # here isn't "two independent roads, pick either", it's "two roads
        # that both happen to cross the ward's one low culvert/bridge over
        # the nullah" -- a common real siting mistake, and also why a
        # hospital and a fire station ended up sited near the same crossing
        # in the first place (a small civic cluster built together near the
        # only bridge). Each facility gets a direct spur to that one
        # chokepoint PLUS a second short service-lane spur that also
        # terminates there (not some other, better-drained junction), so
        # both routes go under together when that one crossing floods. All
        # spur edges are tagged has_drain and non-arterial (smaller
        # residential pipe), compounding the vulnerability further. The
        # shelter (below, unchanged) keeps its original, better-connected
        # placement on the far side of the ward: real disaster-planning
        # guidance sites shelters on safer ground, away from a single
        # chokepoint, and this ward models that contrast deliberately too.
        def add_access_spur(spur_id: str, spur_row: float, spur_col: float, chokepoint: str) -> None:
            lat, lng = self.cell_to_latlng(spur_row, spur_col)
            g.add_node(spur_id, lat=lat, lng=lng, grid_row=spur_row, grid_col=spur_col,
                       is_major_junction=False)
            g.add_edge(spur_id, chokepoint, length_m=edge_length_m(spur_id, chokepoint),
                       is_arterial=False, has_drain=True, edge_id=f"r_{spur_id}_{chokepoint}")

            lane_id = f"{spur_id}_service_lane"
            lane_row, lane_col = spur_row + 0.6, spur_col + 0.6
            lane_lat, lane_lng = self.cell_to_latlng(lane_row, lane_col)
            g.add_node(lane_id, lat=lane_lat, lng=lane_lng, grid_row=lane_row, grid_col=lane_col,
                       is_major_junction=False)
            g.add_edge(spur_id, lane_id, length_m=edge_length_m(spur_id, lane_id),
                       is_arterial=False, has_drain=True, edge_id=f"r_{spur_id}_{lane_id}")
            g.add_edge(lane_id, chokepoint, length_m=edge_length_m(lane_id, chokepoint),
                       is_arterial=False, has_drain=True, edge_id=f"r_{lane_id}_{chokepoint}")

        add_access_spur("hospital_access", 38.4, 66.6, major_junction_nodes[1])  # n_3_4
        add_access_spur("fire_station_access", 46.5, 60.5, major_junction_nodes[1])  # also n_3_4

        return g

    def get_road_graph(self) -> nx.Graph:
        return self._road_graph().copy()

    # ---- critical infrastructure ------------------------------------------

    @lru_cache(maxsize=1)
    def _critical_infra(self) -> tuple[CriticalInfra, ...]:
        # Hospital and fire station sit exactly at their dedicated
        # 2-access-road spur nodes (see _road_graph's add_access_spur) so
        # that redundancy scoring snaps to that deliberately vulnerable
        # node, not some other nearby well-connected intersection. The
        # shelter keeps a fixed, better-connected placement.
        road_graph = self._road_graph()
        hospital = road_graph.nodes["hospital_access"]
        fire_station = road_graph.nodes["fire_station_access"]
        shelter_lat, shelter_lng = self.cell_to_latlng(85, 20)

        points = [
            ("hospital_01", "hospital", "Ward Alpha General Hospital", hospital["lat"], hospital["lng"]),
            ("fire_station_01", "fire_station", "Ward Alpha Fire Station", fire_station["lat"], fire_station["lng"]),
            ("shelter_01", "shelter", "Ward Alpha Community Shelter", shelter_lat, shelter_lng),
        ]
        return tuple(CriticalInfra(i, t, n, lat, lng) for i, t, n, lat, lng in points)

    def get_critical_infrastructure(self) -> list[CriticalInfra]:
        return list(self._critical_infra())
