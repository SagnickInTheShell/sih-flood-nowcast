"""Builds a routable road graph with per-edge travel time, and applies a
flood `state` derived from GNN-predicted node depths via a nearest-
drainage-node spatial join.
"""
from __future__ import annotations

import math

import networkx as nx

from app.core.config import settings

# ASSUMPTION: no posted speed-limit data exists for the synthetic/OSM
# ward, so free-flow travel time uses plausible defaults by road class.
SPEED_MS = {"arterial": 50 / 3.6, "residential": 30 / 3.6}


def build_road_graph(provider) -> nx.Graph:
    g = provider.get_road_graph()
    for _u, _v, data in g.edges(data=True):
        speed = SPEED_MS["arterial"] if data.get("is_arterial") else SPEED_MS["residential"]
        data["base_travel_time_s"] = max(data.get("length_m", 1.0), 1.0) / speed
        data["state"] = "clear"
    return g


def _nearest_drainage_node(lat, lng, drainage_graph):
    best_node, best_d = None, math.inf
    for node, data in drainage_graph.nodes(data=True):
        d = math.hypot(data["lat"] - lat, data["lng"] - lng)
        if d < best_d:
            best_node, best_d = node, d
    return best_node


def apply_flood_state(road_graph: nx.Graph, drainage_graph: nx.DiGraph, node_depth: dict[str, float]) -> nx.Graph:
    node_cache: dict[tuple[float, float], str] = {}
    for u, v, data in road_graph.edges(data=True):
        # BUGFIX: this used to always look up the drainage node nearest to
        # the edge's MIDPOINT -- but when an edge's own endpoints are
        # themselves drainage nodes (the common case for any drain-tagged
        # road edge), the midpoint is often near-exactly equidistant from
        # both, and ties resolve arbitrarily by iteration order. That could
        # pick a dry endpoint over a badly-flooded one just a few metres
        # away (found via the hospital access spur, whose edge to a
        # severely-ponded major junction was being classified "clear").
        # A road edge should flood if EITHER end floods, so when u or v is
        # itself a drainage node, use the worse (max) of their depths
        # directly instead of an external nearest-point lookup.
        u_in_drainage = u in node_depth
        v_in_drainage = v in node_depth
        if u_in_drainage or v_in_drainage:
            depth = max(node_depth.get(u, 0.0), node_depth.get(v, 0.0))
            nearest = u if node_depth.get(u, 0.0) >= node_depth.get(v, 0.0) else v
        else:
            mid_lat = (road_graph.nodes[u]["lat"] + road_graph.nodes[v]["lat"]) / 2
            mid_lng = (road_graph.nodes[u]["lng"] + road_graph.nodes[v]["lng"]) / 2
            key = (round(mid_lat, 6), round(mid_lng, 6))
            if key not in node_cache:
                node_cache[key] = _nearest_drainage_node(mid_lat, mid_lng, drainage_graph)
            nearest = node_cache[key]
            depth = node_depth.get(nearest, 0.0)

        if depth >= settings.DEPTH_THRESHOLD_FLOODED_M:
            state = "flooded"
        elif depth >= settings.DEPTH_THRESHOLD_AT_RISK_M:
            state = "at_risk"
        else:
            state = "clear"
        data["state"] = state
        data["nearest_drainage_node"] = nearest
        data["depth_m"] = depth
    return road_graph
