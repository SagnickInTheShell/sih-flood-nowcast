"""Simple, honest explainability (§8.2's ExplainabilityPanel).

For a given node, re-runs the physics baseline three times with one
factor held at its network-wide median at a time, and reports the
resulting depth delta at that node. This is a basic ablation, not a
black-box SHAP-style claim.
"""
from __future__ import annotations

import statistics

from app.ml.physics_baseline import simulate

RAINFALL_SWEEP_MM_HR = (10, 20, 30, 40, 60, 80, 100, 120)


def explain_node(drainage_graph, catchments, rainfall_intensity_mm_hr: float, duration_min: float, node_id: str) -> list[dict]:
    baseline_result = simulate(drainage_graph, catchments, rainfall_intensity_mm_hr, duration_min)
    baseline_depth = baseline_result.peak_depth().get(node_id, 0.0)

    factors = []

    median_rain = statistics.median(RAINFALL_SWEEP_MM_HR)
    rain_result = simulate(drainage_graph, catchments, median_rain, duration_min)
    rain_depth = rain_result.peak_depth().get(node_id, 0.0)
    factors.append({"factor": "rainfall_intensity", "depth_delta_m": baseline_depth - rain_depth})

    edge_data = list(drainage_graph.edges(data=True))
    if edge_data:
        median_slope = statistics.median(d["slope"] for _, _, d in edge_data)
        slope_graph = drainage_graph.copy()
        for _, _, d in slope_graph.edges(data=True):
            ratio = (median_slope / d["slope"]) ** 0.5 if d["slope"] else 1.0
            d["estimated_capacity_m3_s"] = d["estimated_capacity_m3_s"] * ratio
        slope_result = simulate(slope_graph, catchments, rainfall_intensity_mm_hr, duration_min)
        slope_depth = slope_result.peak_depth().get(node_id, 0.0)
        factors.append({"factor": "local_slope", "depth_delta_m": baseline_depth - slope_depth})

        median_capacity = statistics.median(d["estimated_capacity_m3_s"] for _, _, d in edge_data)
        cap_graph = drainage_graph.copy()
        for _, _, d in cap_graph.edges(data=True):
            d["estimated_capacity_m3_s"] = median_capacity
        cap_result = simulate(cap_graph, catchments, rainfall_intensity_mm_hr, duration_min)
        cap_depth = cap_result.peak_depth().get(node_id, 0.0)
        factors.append({"factor": "drainage_capacity", "depth_delta_m": baseline_depth - cap_depth})

    return factors
