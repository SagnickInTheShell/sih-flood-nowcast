"""Dijkstra and A* routing with flood-state-dependent edge penalties.

edge cost = base_travel_time_s * penalty(state), penalty: clear=1.0,
at_risk=3.0, flooded=inf (§6.7).
"""
from __future__ import annotations

import math

import networkx as nx

PENALTY = {"clear": 1.0, "at_risk": 3.0, "flooded": math.inf}


def edge_cost(data: dict) -> float:
    return data["base_travel_time_s"] * PENALTY.get(data.get("state", "clear"), 1.0)


def _haversine_m(lat1, lng1, lat2, lng2) -> float:
    radius = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    return 2 * radius * math.asin(min(1.0, math.sqrt(a)))


def shortest_path_dijkstra(g: nx.Graph, source, target):
    path = nx.dijkstra_path(g, source, target, weight=lambda u, v, d: edge_cost(d))
    cost = nx.dijkstra_path_length(g, source, target, weight=lambda u, v, d: edge_cost(d))
    return path, cost


def shortest_path_astar(g: nx.Graph, source, target, assumed_speed_ms: float = 50 / 3.6):
    def heuristic(u, v):
        du, dv = g.nodes[u], g.nodes[v]
        return _haversine_m(du["lat"], du["lng"], dv["lat"], dv["lng"]) / assumed_speed_ms

    path = nx.astar_path(g, source, target, heuristic=heuristic, weight=lambda u, v, d: edge_cost(d))
    cost = sum(edge_cost(g.get_edge_data(a, b)) for a, b in zip(path[:-1], path[1:]))
    return path, cost


def nearest_node(g: nx.Graph, lat: float, lng: float) -> str:
    best, best_d = None, math.inf
    for node, data in g.nodes(data=True):
        d = math.hypot(data["lat"] - lat, data["lng"] - lng)
        if d < best_d:
            best, best_d = node, d
    return best


def path_edge_ids(g: nx.Graph, path: list[str]) -> list[str]:
    return [g.get_edge_data(a, b)["edge_id"] for a, b in zip(path[:-1], path[1:])]


def path_flooded_segments(g: nx.Graph, path: list[str]) -> list[str]:
    return [
        g.get_edge_data(a, b)["edge_id"]
        for a, b in zip(path[:-1], path[1:])
        if g.get_edge_data(a, b).get("state") in ("flooded", "at_risk")
    ]


def path_to_geojson_linestring(g: nx.Graph, path: list[str]) -> dict:
    return {"type": "LineString", "coordinates": [[g.nodes[n]["lng"], g.nodes[n]["lat"]] for n in path]}
