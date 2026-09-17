import numpy as np
import torch

from app.ml.model import FloodGNN


def _tiny_batch():
    torch.manual_seed(0)
    x = torch.rand((6, 5))
    edge_index = torch.tensor([[0, 1, 2, 3, 4], [1, 2, 3, 4, 5]], dtype=torch.long)
    edge_weight = torch.rand(5)
    y = torch.rand(6)
    return x, edge_index, edge_weight, y


def test_trains_without_nan_loss():
    model = FloodGNN()
    x, edge_index, edge_weight, y = _tiny_batch()
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    loss = None
    for _ in range(10):
        optimizer.zero_grad()
        pred = model(x, edge_index, edge_weight)
        loss = torch.nn.functional.mse_loss(pred, y)
        loss.backward()
        optimizer.step()
    assert loss is not None
    assert not torch.isnan(loss).item()


def test_mc_dropout_uncertainty_is_nonzero():
    model = FloodGNN()
    x, edge_index, edge_weight, _ = _tiny_batch()
    model.train()  # dropout active, matching ml/infer.py's MC-dropout approach
    preds = []
    with torch.no_grad():
        for _ in range(20):
            preds.append(model(x, edge_index, edge_weight).numpy())
    std = np.stack(preds, axis=0).std(axis=0)
    assert (std > 0).any()
