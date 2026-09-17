"""Simplified kinematic-wave / Muskingum-style routing across the drainage
graph.

This is the ONLY source of "ground truth" in this prototype: it generates
the training labels for the GNN surrogate (ml/train.py) and is also the
sole validation baseline reported in metrics.json. It is a coarse
approximation, not a certified hydraulic model (e.g. SWMM) -- see
docs/JUDGE_QA.md. Never describe its output as observed real-world
flooding.

Algorithm, per node per timestep:
  1. Local catchment runoff (SCS-CN, incremental) is converted to an
     inflow volume for this timestep.
  2. Total water available to route = local inflow + water ponded from
     the previous timestep (so ponded water gets a chance to drain once
     downstream capacity frees up).
  3. Water is pushed downstream through outgoing edges, capped by each
     edge's estimated Manning capacity (converted to a volume for this
     timestep), split proportionally across multiple outgoing edges by
     capacity share.
  4. Whatever can't be routed downstream this step remains "ponded"
     at the node; ponded volume / catchment area gives a depth (m).
     # ASSUMPTION: ponded water is assumed to spread across the node's
     # own contributing catchment area -- a coarse stand-in for a real
     # 2D surface-water spread calculation.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import networkx as nx
import numpy as np

from app.hydrology.scs_cn import runoff_mm
from app.ml.features import Catchment, assign_catchments


@dataclass
class SimulationResult:
    time_min: list[float]
    node_depth_timeseries: dict[str, list[float]]  # node -> depth per timestep (m)
    node_local_inflow_peak_m3_s: dict[str, float]  # naive per-node peak local inflow

    def peak_depth(self) -> dict[str, float]:
        return {n: max(series) if series else 0.0 for n, series in self.node_depth_timeseries.items()}


def _topo_order(g: nx.DiGraph) -> list[str]:
    try:
        return list(nx.topological_sort(g))
    except nx.NetworkXUnfeasible:
        # Break cycles (can arise from elevation ties in flat terrain) by
        # dropping the weakest (highest-slope-tie) edge of each cycle found.
        g = g.copy()
        while True:
            try:
                cycle = nx.find_cycle(g)
            except nx.NetworkXNoCycle:
                break
            g.remove_edge(*cycle[0][:2])
        return list(nx.topological_sort(g))


def simulate(
    drainage_graph: nx.DiGraph,
    catchments: dict[str, Catchment],
    rainfall_intensity_mm_hr: float,
    duration_min: float,
    dt_min: float = 5.0,
    recession_min: float = 60.0,
) -> SimulationResult:
    order = _topo_order(drainage_graph)
    total_min = duration_min + recession_min
    n_steps = int(total_min // dt_min) + 1
    time_min = [i * dt_min for i in range(n_steps)]

    ponded_m3 = {n: 0.0 for n in drainage_graph.nodes}
    depth_series: dict[str, list[float]] = {n: [] for n in drainage_graph.nodes}
    prev_cum_runoff_mm = {n: 0.0 for n in drainage_graph.nodes}
    local_inflow_peak = {n: 0.0 for n in drainage_graph.nodes}

    for t in time_min:
        rain_elapsed_min = min(t, duration_min)
        cum_rain_mm = rainfall_intensity_mm_hr * (rain_elapsed_min / 60.0)

        inflow_this_step_m3 = {}
        for node in drainage_graph.nodes:
            cn = catchments[node].avg_cn
            cum_runoff_mm = runoff_mm(cum_rain_mm, cn)
            incr_mm = max(cum_runoff_mm - prev_cum_runoff_mm[node], 0.0)
            prev_cum_runoff_mm[node] = cum_runoff_mm
            volume_m3 = (incr_mm / 1000.0) * catchments[node].area_m2
            inflow_this_step_m3[node] = volume_m3
            rate_m3_s = volume_m3 / (dt_min * 60.0)
            local_inflow_peak[node] = max(local_inflow_peak[node], rate_m3_s)

        for node in order:
            available_m3 = ponded_m3[node] + inflow_this_step_m3[node]
            out_edges = list(drainage_graph.out_edges(node, data=True))
            total_capacity_m3_s = sum(d["estimated_capacity_m3_s"] for _, _, d in out_edges)
            capacity_volume_m3 = total_capacity_m3_s * dt_min * 60.0

            if not out_edges or total_capacity_m3_s <= 0:
                ponded_m3[node] = available_m3
                continue

            if available_m3 <= capacity_volume_m3:
                outflow_m3 = available_m3
                ponded_m3[node] = 0.0
            else:
                outflow_m3 = capacity_volume_m3
                ponded_m3[node] = available_m3 - capacity_volume_m3

            for _, downstream, edge_data in out_edges:
                share = edge_data["estimated_capacity_m3_s"] / total_capacity_m3_s
                inflow_this_step_m3[downstream] = (
                    inflow_this_step_m3.get(downstream, 0.0) + outflow_m3 * share
                )

        for node in drainage_graph.nodes:
            depth_m = ponded_m3[node] / max(catchments[node].area_m2, 1.0)
            depth_series[node].append(depth_m)

    return SimulationResult(
        time_min=time_min,
        node_depth_timeseries=depth_series,
        node_local_inflow_peak_m3_s=local_inflow_peak,
    )


def run_baseline(provider, drainage_graph, rainfall_intensity_mm_hr, duration_min, dt_min=5.0):
    """Convenience wrapper: assigns catchments then simulates."""
    catchments = assign_catchments(provider, drainage_graph)
    result = simulate(drainage_graph, catchments, rainfall_intensity_mm_hr, duration_min, dt_min)
    return result, catchments
