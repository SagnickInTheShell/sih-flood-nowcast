"""Generates synthetic training scenarios via the physics baseline, trains
the GNN surrogate, and saves a checkpoint + metrics.json.

Sweeps rainfall_intensity x duration per §6.4 of the build spec, splits
80/20 by scenario (not by node, to avoid leakage), trains with early
stopping, and reports MAE/RMSE against the physics baseline -- the only
"ground truth" available in this prototype.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from torch_geometric.data import Data

from app.gis.drainage_graph import build_drainage_graph
from app.gis.synthetic_ward import SyntheticWardProvider
from app.ml.features import assign_catchments, build_node_matrix, build_static_features
from app.ml.model import FloodGNN
from app.ml.physics_baseline import simulate

RAINFALL_INTENSITIES_MM_HR = [10, 20, 30, 40, 60, 80, 100, 120]
DURATIONS_MIN = [30, 60, 90, 120]

MODEL_CAVEAT = "Validated against a simplified physics baseline, not observed real-world flooding."


def generate_scenarios(drainage_graph, catchments, static):
    examples = []
    for intensity in RAINFALL_INTENSITIES_MM_HR:
        for duration in DURATIONS_MIN:
            result = simulate(drainage_graph, catchments, intensity, duration)
            peak = result.peak_depth()
            x = build_node_matrix(static, result.node_local_inflow_peak_m3_s)
            y = np.array([peak[n] for n in static.node_order], dtype=np.float32)
            examples.append({"intensity": intensity, "duration": duration, "x": x, "y": y})
    return examples


def to_pyg(static, example) -> Data:
    edge_index = torch.tensor(static.edge_index, dtype=torch.long)
    edge_weight = torch.tensor(static.edge_capacity_norm, dtype=torch.float32)
    x = torch.tensor(example["x"], dtype=torch.float32)
    y = torch.tensor(example["y"], dtype=torch.float32)
    return Data(x=x, edge_index=edge_index, edge_weight=edge_weight, y=y)


# BUGFIX: plain MSE, averaged uniformly over every node in every scenario,
# let the model collapse to a trivial "predict ~0 everywhere" solution --
# found on real (Bellandur) topology, where only a small fraction of
# node/scenario pairs ever have meaningful depth (most of the ward simply
# doesn't flood at most rainfall levels) and unweighted MSE is already
# nearly minimized by ignoring the few flood-relevant nodes entirely. A
# depth-weighted MSE keeps zero-depth nodes in the loss (correctly
# predicting "clear" still matters) while not letting them drown out the
# gradient signal from the nodes the whole system exists to predict.
def _weighted_mse(pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    weight = 1.0 + 10.0 * target
    return (weight * (pred - target) ** 2).mean()


def train(
    epochs: int = 200, patience: int = 15, lr: float = 1e-3, seed: int = 42, out_dir=None,
    provider=None, drainage_graph=None, catchments=None, static=None,
):
    """Trains against whichever ward is passed in (defaults to the
    synthetic ward, for the standalone `python -m app.ml.train` / seed
    script use case). PILOT_MODE=real must pass its own already-built
    provider/graph/catchments/static (see scenarios/cache.py) -- training
    always against SyntheticWardProvider() regardless of caller was a real
    bug: it silently produced a checkpoint fit to the synthetic ward's
    graph and value distributions, then that same checkpoint got loaded
    for real-ward inference too, via the single shared MODEL_CHECKPOINT_PATH.
    """
    torch.manual_seed(seed)
    if provider is None:
        provider = SyntheticWardProvider()
    if drainage_graph is None:
        drainage_graph = build_drainage_graph(provider)
    if catchments is None:
        catchments = assign_catchments(provider, drainage_graph)
    if static is None:
        static = build_static_features(drainage_graph, catchments)

    examples = generate_scenarios(drainage_graph, catchments, static)
    rng = np.random.RandomState(seed)
    indices = rng.permutation(len(examples))
    split = max(int(0.8 * len(examples)), 1)
    train_idx, val_idx = indices[:split], indices[split:] if split < len(examples) else indices[-1:]

    train_data = [to_pyg(static, examples[i]) for i in train_idx]
    val_data = [to_pyg(static, examples[i]) for i in val_idx]

    model = FloodGNN()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    best_val_loss = float("inf")
    best_state = None
    epochs_since_improve = 0

    for _epoch in range(epochs):
        model.train()
        for data in train_data:
            optimizer.zero_grad()
            pred = model(data.x, data.edge_index, data.edge_weight)
            loss = _weighted_mse(pred, data.y)
            loss.backward()
            optimizer.step()

        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for data in val_data:
                pred = model(data.x, data.edge_index, data.edge_weight)
                val_loss += _weighted_mse(pred, data.y).item()
        val_loss /= max(len(val_data), 1)

        if val_loss < best_val_loss - 1e-6:
            best_val_loss = val_loss
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
            epochs_since_improve = 0
        else:
            epochs_since_improve += 1
            if epochs_since_improve >= patience:
                break

    if best_state is not None:
        model.load_state_dict(best_state)

    model.eval()
    abs_errors, sq_errors = [], []
    with torch.no_grad():
        for data in val_data:
            pred = model(data.x, data.edge_index, data.edge_weight)
            err = (pred - data.y).numpy()
            abs_errors.extend(np.abs(err).tolist())
            sq_errors.extend((err ** 2).tolist())
    mae = float(np.mean(abs_errors)) if abs_errors else 0.0
    rmse = float(np.sqrt(np.mean(sq_errors))) if sq_errors else 0.0

    out_dir = Path(out_dir or Path(__file__).parent / "checkpoints")
    out_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = out_dir / "gnn_surrogate.pt"
    torch.save(model.state_dict(), checkpoint_path)

    metrics = {
        "mae_m": mae,
        "rmse_m": rmse,
        "n_train_scenarios": len(train_data),
        "n_val_scenarios": len(val_data),
        "best_val_loss": best_val_loss,
        "caveat": MODEL_CAVEAT,
    }
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))

    return model, metrics


if __name__ == "__main__":
    _, result_metrics = train()
    print(json.dumps(result_metrics, indent=2))
