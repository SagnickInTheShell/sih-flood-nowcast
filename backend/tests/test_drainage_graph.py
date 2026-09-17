import networkx as nx

from app.gis.drainage_graph import build_drainage_graph
from app.gis.synthetic_ward import SyntheticWardProvider


def _graph():
    return build_drainage_graph(SyntheticWardProvider())


def test_single_connected_component():
    g = _graph()
    assert nx.number_connected_components(g.to_undirected()) == 1


def test_no_orphan_nodes():
    g = _graph()
    assert len(g.nodes) > 0
    assert all(g.degree(n) > 0 for n in g.nodes)


def test_all_edges_positive_capacity():
    g = _graph()
    assert len(g.edges) > 0
    assert all(d["estimated_capacity_m3_s"] > 0 for _, _, d in g.edges(data=True))


def test_outlet_is_set():
    g = _graph()
    assert g.graph["outlet_node"] in g.nodes
