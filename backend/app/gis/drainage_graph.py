"""Builds the drainage network graph: a directed sub-graph of the road
network restricted to drain-tagged edges, with per-edge hydraulic
capacity estimated via Manning's equation for an assumed pipe.

# ASSUMPTION (see §6.3 / config.py): pipe diameters are not measured for
# any real ward. DRAIN_DIAMETER_RESIDENTIAL_MM / DRAIN_DIAMETER_ARTERIAL_MM
# are plausible defaults for a planned residential layout, configurable.
"""
from __future__ import annotations

import math

import networkx as nx

from app.core.config import settings
from app.gis.ward_provider import WardDataProvider


def manning_capacity_m3_s(diameter_mm: float, slope: float, mannings_n: float) -> float:
    """Full-flow capacity of a circular pipe via Manning's equation."""
    d = diameter_mm / 1000.0
    area = math.pi * d ** 2 / 4.0
    hydraulic_radius = d / 4.0  # full circular pipe
    slope = max(slope, 1e-4)
    return (1.0 / mannings_n) * area * hydraulic_radius ** (2 / 3) * slope ** 0.5


def _node_elevation(road_graph: nx.Graph, node: str, elevation_grid) -> float:
    data = road_graph.nodes[node]
    gr, gc = data.get("grid_row"), data.get("grid_col")
    if gr is None:
        return 0.0
    r0 = min(max(int(round(gr)), 0), elevation_grid.shape[0] - 1)
    c0 = min(max(int(round(gc)), 0), elevation_grid.shape[1] - 1)
    return float(elevation_grid[r0, c0])


def _ensure_major_junctions_tagged(road_graph: nx.Graph) -> None:
    """Every major junction must have at least one drain-tagged incident
    edge, otherwise it can never appear in the drainage graph."""
    for node, data in road_graph.nodes(data=True):
        if not data.get("is_major_junction"):
            continue
        incident = list(road_graph.edges(node, data=True))
        if not any(d.get("has_drain") for _, _, d in incident):
            if incident:
                _, _, first = incident[0]
                first["has_drain"] = True


def _fill_spurious_sinks(g: nx.DiGraph, legitimate_sinks: set[str]) -> None:
    """Standard depression-filling, applied to the drainage graph directly
    rather than the raster (see dem.py's load_and_process_raster for the
    pysheds equivalent on real rasters -- the in-memory synthetic/real grid
    path here needs its own version).

    Directing every edge strictly hi->lo elevation creates a local sink
    wherever a node happens to be lower than ALL of its few neighbours
    (most often grid corners with only 2-3 connections), even when that
    node's absolute elevation is nowhere near the ward's true low point.
    Such a node accumulates 100% of its inflow forever with no outlet,
    which is physically wrong (a real depression fills until it overflows
    its lowest rim) and, in this ward, was drowning out the actual
    drainage-channel vulnerability the critical infrastructure is sited
    against.

    `legitimate_sinks` (the 4 major junctions along the depression, not
    just the single globally-lowest node) are left alone: a real drainage
    channel has multiple points along its length where local sub-
    catchments empty into it, not one single terminus, so treating only
    the global minimum as a "real" sink was itself an oversimplification
    that collapsed the depression's 4 designed low points down to
    effectively one. Every OTHER zero-out-degree node gets a single
    overflow edge to its lowest neighbour, reusing that neighbour's edge
    capacity -- emulating "fills, then spills over its lowest rim" rather
    than leaving it an unphysical infinite pit.
    """
    for node in list(g.nodes):
        if node in legitimate_sinks or g.out_degree(node) > 0:
            continue
        neighbors = list(g.predecessors(node))
        if not neighbors:
            continue
        overflow_target = min(neighbors, key=lambda nb: g.nodes[nb]["elevation_m"])
        inbound = g.get_edge_data(overflow_target, node)
        g.add_edge(
            node, overflow_target,
            length_m=inbound["length_m"],
            slope=max(abs(g.nodes[node]["elevation_m"] - g.nodes[overflow_target]["elevation_m"]) / inbound["length_m"], 1e-3),
            estimated_capacity_m3_s=inbound["estimated_capacity_m3_s"],
            edge_id=f"overflow_{node}_{overflow_target}",
            is_arterial=inbound.get("is_arterial", False),
        )


def _ensure_single_component(road_graph: nx.Graph, drain_edges: set[frozenset]) -> set[frozenset]:
    """Merge disconnected drainage components by promoting the shortest
    connecting path (over the full, always-connected road graph) between
    each minority component and the largest one to drain-tagged."""
    sub = nx.Graph()
    sub.add_edges_from(tuple(e) for e in drain_edges)
    components = list(nx.connected_components(sub))
    if len(components) <= 1:
        return drain_edges

    components.sort(key=len, reverse=True)
    main = set(components[0])
    for comp in components[1:]:
        best_path = None
        for src in comp:
            lengths, paths = nx.single_source_dijkstra(road_graph, src, weight="length_m")
            for target in main:
                if target in paths:
                    path = paths[target]
                    if best_path is None or len(path) < len(best_path):
                        best_path = path
        if best_path:
            for a, b in zip(best_path[:-1], best_path[1:]):
                drain_edges.add(frozenset((a, b)))
            main |= comp
    return drain_edges


def build_drainage_graph(provider: WardDataProvider) -> nx.DiGraph:
    road_graph = provider.get_road_graph()
    elevation_grid = provider.get_elevation_grid()

    _ensure_major_junctions_tagged(road_graph)

    drain_edges = {
        frozenset((u, v))
        for u, v, data in road_graph.edges(data=True)
        if data.get("has_drain")
    }
    drain_edges = _ensure_single_component(road_graph, drain_edges)

    g = nx.DiGraph()
    drain_nodes = set()
    for e in drain_edges:
        drain_nodes.update(e)

    for node in drain_nodes:
        data = road_graph.nodes[node]
        g.add_node(
            node,
            lat=data["lat"],
            lng=data["lng"],
            grid_row=data.get("grid_row"),
            grid_col=data.get("grid_col"),
            elevation_m=_node_elevation(road_graph, node, elevation_grid),
            is_major_junction=data.get("is_major_junction", False),
        )

    for e in drain_edges:
        u, v = tuple(e)
        edge_data = road_graph.get_edge_data(u, v)
        length_m = max(edge_data.get("length_m", 1.0), 1.0)
        eu, ev = g.nodes[u]["elevation_m"], g.nodes[v]["elevation_m"]
        hi, lo = (u, v) if eu >= ev else (v, u)
        slope = max(abs(eu - ev) / length_m, 1e-3)
        is_trunk = g.nodes[u].get("is_major_junction") and g.nodes[v].get("is_major_junction")
        if is_trunk:
            diameter_mm = settings.DRAIN_DIAMETER_TRUNK_MM
        elif edge_data.get("is_arterial"):
            diameter_mm = settings.DRAIN_DIAMETER_ARTERIAL_MM
        else:
            diameter_mm = settings.DRAIN_DIAMETER_RESIDENTIAL_MM
        capacity = manning_capacity_m3_s(diameter_mm, slope, settings.MANNINGS_N_CONCRETE)
        g.add_edge(
            hi, lo,
            length_m=length_m,
            slope=slope,
            estimated_capacity_m3_s=capacity,
            edge_id=edge_data.get("edge_id", f"r_{hi}_{lo}"),
            is_arterial=edge_data.get("is_arterial", False),
        )

    # outlet_node (informational) is the single globally lowest point;
    # legitimate_sinks (used for sink-filling) is broader -- see
    # _fill_spurious_sinks for why the 4 major junctions all qualify.
    outlet = min(g.nodes, key=lambda n: g.nodes[n]["elevation_m"])
    g.graph["outlet_node"] = outlet
    legitimate_sinks = {n for n, d in g.nodes(data=True) if d.get("is_major_junction")} or {outlet}
    _fill_spurious_sinks(g, legitimate_sinks)

    return g
