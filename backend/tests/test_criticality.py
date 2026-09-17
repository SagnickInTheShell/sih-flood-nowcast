import networkx as nx

from app.gis.ward_provider import CriticalInfra
from app.routing.criticality import check_critical_access


def _graph(cut: bool) -> nx.Graph:
    g = nx.Graph()
    coords = {
        "hospital": (0.0, 0.0), "junction": (0.0, 0.01), "arterial": (0.0, 0.02),
        "alt": (0.01, 0.01),
    }
    for n, (lat, lng) in coords.items():
        g.add_node(n, lat=lat, lng=lng)
    g.add_edge(
        "hospital", "junction", length_m=100, base_travel_time_s=10,
        state="flooded" if cut else "clear", edge_id="e_hj", is_arterial=False,
    )
    g.add_edge("junction", "arterial", length_m=100, base_travel_time_s=10, state="clear", edge_id="e_ja", is_arterial=True)
    if not cut:
        g.add_edge("hospital", "alt", length_m=120, base_travel_time_s=12, state="clear", edge_id="e_ha", is_arterial=False)
        g.add_edge("alt", "arterial", length_m=120, base_travel_time_s=12, state="clear", edge_id="e_aa", is_arterial=True)
    return g


def test_zero_redundancy_raises_risk():
    g = _graph(cut=True)
    infra = [CriticalInfra("hospital_01", "hospital", "Test Hospital", 0.0, 0.0)]
    risks = check_critical_access(g, infra)
    assert len(risks) == 1
    assert risks[0].access_redundancy_score == 0


def test_alternate_path_prevents_risk():
    g = _graph(cut=False)
    infra = [CriticalInfra("hospital_01", "hospital", "Test Hospital", 0.0, 0.0)]
    risks = check_critical_access(g, infra)
    assert risks == []
