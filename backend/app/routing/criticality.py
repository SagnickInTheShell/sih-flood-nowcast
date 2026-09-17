"""Criticality-weighted access (§6.7, required unique feature).

For each critical-infrastructure node, computes an access redundancy
score = number of edge-disjoint paths from that node to the arterial
road network as a whole (via a virtual sink node, see
compute_access_redundancy) under the current flood state. A score of 0
raises a CriticalAccessRisk -- a distinct, clearly-flagged object, never
folded into generic routing output.
"""
from __future__ import annotations

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


_ARTERIAL_SINK = "__arterial_sink__"


def compute_access_redundancy(road_graph: nx.Graph, infra_lat: float, infra_lng: float) -> int:
    """Edge-disjoint paths from the infra node to the arterial network as a
    whole, via a virtual sink wired to every arterial-tagged endpoint
    (excluding the infra node itself, if it happens to sit on an arterial).

    # BUGFIX: an earlier version picked the single geometrically nearest
    # arterial node and short-circuited to score=1 whenever the infra node
    # WAS that nearest node -- which happens by construction here, since
    # the synthetic ward's critical infrastructure sits directly on the
    # two arterial diagonals. That made the score ignore flood state
    # entirely: it stayed 1 even with every road edge flooded. Routing
    # through a virtual sink instead means the score reflects how many of
    # the infra node's own (flood-state-dependent) edges actually still
    # lead somewhere, so it correctly reaches 0 under total flooding.
    """
    passable = _passable_subgraph(road_graph)
    infra_node = nearest_node(passable, infra_lat, infra_lng)

    arterial_endpoints = set()
    for u, v, data in road_graph.edges(data=True):
        if data.get("is_arterial"):
            arterial_endpoints.add(u)
            arterial_endpoints.add(v)
    arterial_endpoints.discard(infra_node)

    if not arterial_endpoints:
        return 1

    g = passable.copy()
    g.add_node(_ARTERIAL_SINK)
    for node in arterial_endpoints:
        if node in g:
            g.add_edge(node, _ARTERIAL_SINK)

    if not nx.has_path(g, infra_node, _ARTERIAL_SINK):
        return 0
    return len(list(nx.edge_disjoint_paths(g, infra_node, _ARTERIAL_SINK)))


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
