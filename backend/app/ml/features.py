"""Node/edge feature engineering shared by the physics baseline (label
generator) and the GNN surrogate.

Each fine DEM grid cell is assigned to its nearest drainage-graph node
(a simple Voronoi/nearest-neighbor catchment split by grid coordinate)
so every drainage node gets a contributing area and an average curve
number to drive SCS-CN runoff.
"""
from __future__ import annotations

from dataclasses import dataclass

import networkx as nx
import numpy as np

from app.gis.dem import process_dem
from app.gis.ward_provider import WardDataProvider


@dataclass
class Catchment:
    node: str
    n_cells: int
    area_m2: float
    avg_cn: float
    flow_accumulation: float
    slope_pct: float


def assign_catchments(provider: WardDataProvider, drainage_graph: nx.DiGraph) -> dict[str, Catchment]:
    elevation_grid = provider.get_elevation_grid()
    cn_grid = provider.get_curve_number_grid()
    resolution = provider.grid_resolution_m()
    dem_layers = process_dem(elevation_grid, resolution)

    nodes = list(drainage_graph.nodes(data=True))
    node_ids = [n for n, _ in nodes]
    node_rc = np.array([[d["grid_row"], d["grid_col"]] for _, d in nodes], dtype=float)

    n_rows, n_cols = elevation_grid.shape
    rows, cols = np.meshgrid(np.arange(n_rows), np.arange(n_cols), indexing="ij")
    rows_f = rows.ravel().astype(float)
    cols_f = cols.ravel().astype(float)

    # nearest drainage node per cell (vectorized brute force -- grids here are small)
    dists = np.sqrt(
        (rows_f[:, None] - node_rc[None, :, 0]) ** 2
        + (cols_f[:, None] - node_rc[None, :, 1]) ** 2
    )
    nearest = np.argmin(dists, axis=1)

    cn_flat = cn_grid.ravel()
    facc_flat = dem_layers["flow_accumulation"].ravel()
    slope_flat = dem_layers["slope"].ravel()

    catchments: dict[str, Catchment] = {}
    for idx, node in enumerate(node_ids):
        mask = nearest == idx
        n_cells = int(mask.sum())
        if n_cells == 0:
            # Guaranteed at least the node's own cell, in case of ties.
            n_cells = 1
            avg_cn = float(cn_grid[int(round(node_rc[idx, 0])), int(round(node_rc[idx, 1]))])
            facc = float(dem_layers["flow_accumulation"][int(round(node_rc[idx, 0])), int(round(node_rc[idx, 1]))])
            slope = float(dem_layers["slope"][int(round(node_rc[idx, 0])), int(round(node_rc[idx, 1]))])
        else:
            avg_cn = float(cn_flat[mask].mean())
            facc = float(facc_flat[mask].max())
            slope = float(slope_flat[mask].mean())
        # ASSUMPTION: on the synthetic ward's regular 8x8 road grid, nearest-
        # node Voronoi catchments are all a similar, sane size. Real OSM
        # topology has much less regular node spacing -- a cluster of
        # closely-packed nodes describing one complex junction can each get
        # a catchment of just a handful of raster cells (a few hundred m2,
        # smaller than a single building footprint). Since ponding depth is
        # volume/area, that produces physically meaningless multi-metre
        # "flood depths" at those specific nodes -- a real limitation of
        # this simplified nearest-node catchment split on irregular real
        # topology, not a hidden or smoothed-over data problem (see
        # docs/DATA_SOURCES.md). A floor of a few raster cells wasn't
        # enough -- verified against the physics baseline directly, a real
        # junction converging 3 substantial upstream drainage lines onto a
        # ~350m2 catchment still produced tens of metres of "depth", which
        # is not physically credible for any urban flood. 10,000 m2 (1
        # hectare) is a coarse floor representing the minimum plausible
        # immediate contributing area for any real road intersection --
        # the nearest-node Voronoi split simply isn't precise enough on
        # irregular real topology to trust at finer granularity than that.
        min_area_m2 = 10_000.0
        area_m2 = max(n_cells * resolution ** 2, min_area_m2)

        catchments[node] = Catchment(
            node=node,
            n_cells=n_cells,
            area_m2=area_m2,
            avg_cn=avg_cn,
            flow_accumulation=facc,
            slope_pct=slope,
        )
    return catchments


def normalize(values: np.ndarray) -> np.ndarray:
    lo, hi = float(values.min()), float(values.max())
    if hi - lo < 1e-9:
        return np.zeros_like(values)
    return (values - lo) / (hi - lo)


@dataclass
class StaticGraphFeatures:
    """Everything about the drainage graph that does NOT depend on the
    rainfall scenario -- computed once, reused across every scenario."""
    node_order: list[str]
    elevation_norm: np.ndarray
    cn_over_100: np.ndarray
    slope_pct: np.ndarray
    flow_accumulation_norm: np.ndarray
    edge_index: np.ndarray  # (2, E)
    edge_length_norm: np.ndarray
    edge_slope: np.ndarray
    edge_capacity_norm: np.ndarray
    edge_ids: list[str]


def build_static_features(drainage_graph: nx.DiGraph, catchments: dict[str, Catchment]) -> StaticGraphFeatures:
    node_order = list(drainage_graph.nodes)
    index_of = {n: i for i, n in enumerate(node_order)}

    elevations = np.array([drainage_graph.nodes[n]["elevation_m"] for n in node_order])
    slopes = np.array([catchments[n].slope_pct for n in node_order])
    cns = np.array([catchments[n].avg_cn for n in node_order])
    faccs = np.array([catchments[n].flow_accumulation for n in node_order])

    edges = list(drainage_graph.edges(data=True))
    edge_index = np.array([[index_of[u], index_of[v]] for u, v, _ in edges]).T if edges else np.zeros((2, 0), dtype=int)
    lengths = np.array([d["length_m"] for _, _, d in edges]) if edges else np.zeros(0)
    edge_slopes = np.array([d["slope"] for _, _, d in edges]) if edges else np.zeros(0)
    capacities = np.array([d["estimated_capacity_m3_s"] for _, _, d in edges]) if edges else np.zeros(0)
    edge_ids = [d["edge_id"] for _, _, d in edges]

    return StaticGraphFeatures(
        node_order=node_order,
        elevation_norm=normalize(elevations),
        cn_over_100=cns / 100.0,
        slope_pct=slopes,
        flow_accumulation_norm=normalize(faccs),
        edge_index=edge_index,
        edge_length_norm=normalize(lengths) if lengths.size else lengths,
        edge_slope=edge_slopes,
        edge_capacity_norm=normalize(capacities) if capacities.size else capacities,
        edge_ids=edge_ids,
    )


def build_node_matrix(static: StaticGraphFeatures, local_inflow_m3_s: dict[str, float]) -> np.ndarray:
    """(N, 5) node feature matrix: [elevation_norm, cn/100, slope, flow_acc_norm, local_inflow_m3_s]."""
    inflow = np.array([local_inflow_m3_s.get(n, 0.0) for n in static.node_order])
    return np.stack(
        [static.elevation_norm, static.cn_over_100, static.slope_pct, static.flow_accumulation_norm, inflow],
        axis=1,
    ).astype(np.float32)
