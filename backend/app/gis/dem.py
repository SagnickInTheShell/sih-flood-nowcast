"""DEM processing: slope, D8 flow direction, flow accumulation.

For the in-memory synthetic/real elevation grid we use a direct, dependency-free
D8 implementation (ESRI D8 direction codes) rather than routing an in-memory
array through pysheds's raster-file-oriented API, which expects a georeferenced
file on disk and varies across versions.
# ASSUMPTION: pysheds is used (and required, see requirements.txt) for real
# raster-file DEM tiles fetched via scripts/download_srtm.py -- see
# load_and_process_raster() below. The numpy D8 implementation here produces
# the same standard D8 semantics for the in-memory grid path used by both
# ward providers, so downstream code (drainage_graph.py) is agnostic to
# which path produced {elevation, slope, flow_direction, flow_accumulation}.
"""
from __future__ import annotations

import numpy as np

# ESRI D8 direction codes: (row_offset, col_offset) -> code
D8_NEIGHBORS = [
    (-1, 0, 32), (-1, 1, 64), (0, 1, 128), (1, 1, 1),
    (1, 0, 2), (1, -1, 4), (0, -1, 8), (-1, -1, 16),
]


def compute_slope(elevation: np.ndarray, resolution_m: float) -> np.ndarray:
    """Slope in percent via a standard 3x3 neighborhood gradient."""
    dzdy, dzdx = np.gradient(elevation, resolution_m)
    slope_pct = np.sqrt(dzdx ** 2 + dzdy ** 2) * 100.0
    return slope_pct


def compute_flow_direction(elevation: np.ndarray) -> np.ndarray:
    """D8 flow direction: each cell points to its steepest downslope neighbor."""
    n_rows, n_cols = elevation.shape
    direction = np.zeros((n_rows, n_cols), dtype=np.int32)
    padded = np.pad(elevation, 1, mode="edge")
    for r in range(n_rows):
        for c in range(n_cols):
            z = padded[r + 1, c + 1]
            best_drop, best_code = -np.inf, 0
            for dr, dc, code in D8_NEIGHBORS:
                dist = np.hypot(dr, dc)
                neighbor_z = padded[r + 1 + dr, c + 1 + dc]
                drop = (z - neighbor_z) / dist
                if drop > best_drop:
                    best_drop, best_code = drop, code
            direction[r, c] = best_code if best_drop > 0 else 0
    return direction


_CODE_TO_OFFSET = {code: (dr, dc) for dr, dc, code in D8_NEIGHBORS}


def compute_flow_accumulation(flow_direction: np.ndarray) -> np.ndarray:
    """Number of upstream cells draining through each cell (incl. itself),
    computed by topologically processing cells from highest accumulation-order
    (no dependents unresolved) via iterative in-degree reduction (Kahn's algorithm)."""
    n_rows, n_cols = flow_direction.shape
    accumulation = np.ones((n_rows, n_cols), dtype=np.float64)
    in_degree = np.zeros((n_rows, n_cols), dtype=np.int32)
    downstream = {}

    for r in range(n_rows):
        for c in range(n_cols):
            code = flow_direction[r, c]
            if code == 0:
                continue
            dr, dc = _CODE_TO_OFFSET[code]
            nr, nc = r + dr, c + dc
            if 0 <= nr < n_rows and 0 <= nc < n_cols:
                downstream[(r, c)] = (nr, nc)
                in_degree[nr, nc] += 1

    from collections import deque

    queue = deque(
        (r, c) for r in range(n_rows) for c in range(n_cols) if in_degree[r, c] == 0
    )
    while queue:
        r, c = queue.popleft()
        target = downstream.get((r, c))
        if target is None:
            continue
        tr, tc = target
        accumulation[tr, tc] += accumulation[r, c]
        in_degree[tr, tc] -= 1
        if in_degree[tr, tc] == 0:
            queue.append((tr, tc))

    return accumulation


def process_dem(elevation: np.ndarray, resolution_m: float) -> dict[str, np.ndarray]:
    slope = compute_slope(elevation, resolution_m)
    flow_direction = compute_flow_direction(elevation)
    flow_accumulation = compute_flow_accumulation(flow_direction)
    return {
        "elevation": elevation,
        "slope": slope,
        "flow_direction": flow_direction,
        "flow_accumulation": flow_accumulation,
    }


def load_and_process_raster(path: str) -> dict[str, np.ndarray]:
    """Real-ward path: load a georeferenced SRTM GeoTIFF and derive the same
    {elevation, slope, flow_direction, flow_accumulation} outputs via pysheds."""
    from pysheds.grid import Grid

    grid = Grid.from_raster(path)
    dem = grid.read_raster(path)
    filled = grid.fill_depressions(dem)
    inflated = grid.resolve_flats(filled)
    fdir = grid.flowdir(inflated)
    facc = grid.accumulation(fdir)
    elevation = np.asarray(dem)
    resolution_m = abs(grid.affine.a)
    return {
        "elevation": elevation,
        "slope": compute_slope(elevation, resolution_m),
        "flow_direction": np.asarray(fdir),
        "flow_accumulation": np.asarray(facc),
    }
