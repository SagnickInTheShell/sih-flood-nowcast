import math

import networkx as nx
import pytest

from app.routing.router import shortest_path_astar, shortest_path_dijkstra


def _hand_built_graph():
    g = nx.Graph()
    coords = {
        "A": (0.0, 0.0), "B": (0.0, 0.01), "C": (0.0, 0.02),
        "D": (0.01, 0.0), "E": (0.01, 0.02),
    }
    for n, (lat, lng) in coords.items():
        g.add_node(n, lat=lat, lng=lng)
    # A-B-C is the direct path; A-D-E-C is the detour.
    g.add_edge("A", "B", length_m=100, base_travel_time_s=10, state="flooded", edge_id="e_ab", is_arterial=False)
    g.add_edge("B", "C", length_m=100, base_travel_time_s=10, state="clear", edge_id="e_bc", is_arterial=False)
    g.add_edge("A", "D", length_m=150, base_travel_time_s=15, state="clear", edge_id="e_ad", is_arterial=False)
    g.add_edge("D", "E", length_m=150, base_travel_time_s=15, state="clear", edge_id="e_de", is_arterial=False)
    g.add_edge("E", "C", length_m=150, base_travel_time_s=15, state="clear", edge_id="e_ec", is_arterial=False)
    return g


def test_router_avoids_flooded_edge():
    g = _hand_built_graph()
    path, cost = shortest_path_dijkstra(g, "A", "C")
    assert "B" not in path
    assert cost < math.inf


def test_astar_and_dijkstra_agree_when_all_clear():
    g = _hand_built_graph()
    for _, _, d in g.edges(data=True):
        d["state"] = "clear"
    _, cost_d = shortest_path_dijkstra(g, "A", "C")
    _, cost_a = shortest_path_astar(g, "A", "C")
    assert cost_a == pytest.approx(cost_d)
