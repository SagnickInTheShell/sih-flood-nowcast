#!/usr/bin/env python3
"""Generates the deterministic synthetic ward, builds its drainage graph,
trains the GNN surrogate checkpoint, and prints a summary -- run this once
before the first `uvicorn app.main:app` so /api/scenarios has a trained
checkpoint to load (falls back to an untrained model otherwise, which
still runs but with meaningless predictions).

Usage (from backend/):
    python ../scripts/seed_synthetic_ward.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.gis.drainage_graph import build_drainage_graph  # noqa: E402
from app.gis.synthetic_ward import SyntheticWardProvider  # noqa: E402
from app.ml.train import train  # noqa: E402


def main() -> None:
    provider = SyntheticWardProvider()
    elevation = provider.get_elevation_grid()
    graph = build_drainage_graph(provider)
    infra = provider.get_critical_infrastructure()

    print("Synthetic Reference Ward (seed=%d)" % provider.seed)
    print(f"  Elevation range: {elevation.min():.2f}m - {elevation.max():.2f}m")
    print(f"  Road network nodes: {len(provider.get_road_graph().nodes)}")
    print(f"  Drainage graph nodes: {len(graph.nodes)}, edges: {len(graph.edges)}")
    print(f"  Critical infrastructure: {[i.name for i in infra]}")
    print()
    print("Training GNN surrogate against the physics baseline...")

    checkpoint_dir = Path(__file__).resolve().parent.parent / "backend" / "app" / "ml" / "checkpoints" / "synthetic"
    _, metrics = train(out_dir=checkpoint_dir)
    print("Training complete:")
    for k, v in metrics.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
