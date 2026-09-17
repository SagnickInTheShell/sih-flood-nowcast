"""Criticality-weighted access (§6.7, required unique feature).

For each critical-infrastructure node, computes an access redundancy
score = number of edge-disjoint paths from that node to the nearest
arterial road under the current flood state. A score of 0 raises a
CriticalAccessRisk -- a distinct, clearly-flagged object, never folded
into generic routing output.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import networkx as nx

from app.routing.router import nearest_node


@dataclass
class CriticalAccessRisk:
    infra_id: str
    infra_type: str
    infra_name: str
    access_redundancy_score: int
    message: str


def _passable_subgraph(road_graph: nx.Graph) -> nx.Graph:
    """Flooded edges are removed entirely; at_risk edges stay passable
    (just penalized elsewhere for routing-cost purposes)."""
    g = nx.Graph()
    g.add_nodes_from(road_graph.nodes(data=True))
    for u, v, data in road_graph.edges(data=True):
        if data.get("state") != "flooded":
            g.add_edge(u, v, **data)
    return g


def _nearest_arterial_node(road_graph: nx.Graph, from_node: str) -> str | None:
    best, best_d = None, math.inf
    src = road_graph.nodes[from_node]
    for u, v, data in road_graph.edges(data=True):
        if not data.get("is_arterial"):
            continue
        for cand in (u, v):
            cd = road_graph.nodes[cand]
            d = math.hypot(cd["lat"] - src["lat"], cd["lng"] - src["lng"])
            if d < best_d:
                best, best_d = cand, d
    return best


def compute_access_redundancy(road_graph: nx.Graph, infra_lat: float, infra_lng: float) -> int:
    passable = _passable_subgraph(road_graph)
    infra_node = nearest_node(passable, infra_lat, infra_lng)
    arterial_node = _nearest_arterial_node(road_graph, infra_node)
    if arterial_node is None or infra_node == arterial_node:
        return 1
    if not nx.has_path(passable, infra_node, arterial_node):
        return 0
    return len(list(nx.edge_disjoint_paths(passable, infra_node, arterial_node)))


def check_critical_access(road_graph: nx.Graph, critical_infra: list) -> list[CriticalAccessRisk]:
    risks = []
    for infra in critical_infra:
        score = compute_access_redundancy(road_graph, infra.lat, infra.lng)
        if score == 0:
            label = infra.infra_type.replace("_", " ")
            risks.append(CriticalAccessRisk(
                infra_id=infra.infra_id,
                infra_type=infra.infra_type,
                infra_name=infra.name,
                access_redundancy_score=0,
                message=f"No flood-free path currently reaches this {label}.",
            ))
    return risks
