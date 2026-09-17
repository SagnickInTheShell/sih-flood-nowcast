"""GNN surrogate architecture (PyTorch Geometric).

3x GCNConv (hidden=64) + ReLU + Dropout(0.2), final Linear(64, 1) -> predicted
water depth (m) per node.

# ASSUMPTION: GCNConv only accepts a single scalar `edge_weight`, not the
# full 3-dim edge feature vector described in §6.5. We combine the 3 edge
# features into one hydraulic-relevance scalar (capacity_m3_s_normalized,
# the most physically decisive of the three for whether water backs up)
# and pass that as edge_weight. All 3 raw edge features are still computed
# and stored (see features.py / physics_baseline.py) and surfaced in the
# explainability panel; this is a documented simplification of the GNN's
# own input, not a loss of the underlying data.
"""
from __future__ import annotations

import torch
import torch.nn.functional as F
from torch_geometric.nn import GCNConv

NODE_FEATURE_DIM = 5
HIDDEN_DIM = 64
DROPOUT_P = 0.2


class FloodGNN(torch.nn.Module):
    def __init__(self, node_in: int = NODE_FEATURE_DIM, hidden: int = HIDDEN_DIM, dropout: float = DROPOUT_P):
        super().__init__()
        self.conv1 = GCNConv(node_in, hidden)
        self.conv2 = GCNConv(hidden, hidden)
        self.conv3 = GCNConv(hidden, hidden)
        self.out = torch.nn.Linear(hidden, 1)
        self.dropout = dropout

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor, edge_weight: torch.Tensor | None = None) -> torch.Tensor:
        x = F.relu(self.conv1(x, edge_index, edge_weight))
        x = F.dropout(x, p=self.dropout, training=self.training)
        x = F.relu(self.conv2(x, edge_index, edge_weight))
        x = F.dropout(x, p=self.dropout, training=self.training)
        x = F.relu(self.conv3(x, edge_index, edge_weight))
        x = F.dropout(x, p=self.dropout, training=self.training)
        depth = self.out(x).squeeze(-1)
        return F.relu(depth)  # depth cannot be negative
