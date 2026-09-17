"""Loads the trained checkpoint and predicts water depth with uncertainty.

Uncertainty via Monte Carlo Dropout: dropout is kept active at inference
time (model.train() mode, no grad), N stochastic forward passes are run,
and the per-node mean/std across those passes is the confidence band.
This is required by §6.5 -- never a constant placeholder.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import torch

from app.core.config import settings
from app.ml.features import StaticGraphFeatures, assign_catchments, build_node_matrix
from app.ml.model import FloodGNN
from app.ml.physics_baseline import simulate


def load_model(checkpoint_path: str | None = None) -> tuple[FloodGNN, bool]:
    """Returns (model, checkpoint_found)."""
    model = FloodGNN()
    path = Path(checkpoint_path or settings.MODEL_CHECKPOINT_PATH)
    if path.exists():
        model.load_state_dict(torch.load(path, map_location="cpu", weights_only=True))
        return model, True
    return model, False


def mc_dropout_predict(model: FloodGNN, x, edge_index, edge_weight, n_samples: int | None = None):
    n_samples = n_samples or settings.MC_DROPOUT_SAMPLES
    model.train()  # keep dropout active during inference, by design
    preds = []
    with torch.no_grad():
        for _ in range(n_samples):
            preds.append(model(x, edge_index, edge_weight).numpy())
    preds = np.stack(preds, axis=0)
    return preds.mean(axis=0), preds.std(axis=0)


def predict_scenario(
    provider,
    drainage_graph,
    static: StaticGraphFeatures,
    model: FloodGNN,
    rainfall_intensity_mm_hr: float,
    duration_min: float,
):
    catchments = assign_catchments(provider, drainage_graph)
    baseline_result = simulate(drainage_graph, catchments, rainfall_intensity_mm_hr, duration_min)

    x = torch.tensor(
        build_node_matrix(static, baseline_result.node_local_inflow_peak_m3_s), dtype=torch.float32
    )
    edge_index = torch.tensor(static.edge_index, dtype=torch.long)
    edge_weight = torch.tensor(static.edge_capacity_norm, dtype=torch.float32)

    mean, std = mc_dropout_predict(model, x, edge_index, edge_weight)

    return {
        "node_order": static.node_order,
        "depth_mean": mean,
        "depth_std": std,
        "baseline_result": baseline_result,
    }
