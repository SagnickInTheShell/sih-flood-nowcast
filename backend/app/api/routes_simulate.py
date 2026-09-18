from __future__ import annotations

from fastapi import APIRouter

from app.api.schemas import NodePrediction, RoadSegment, SimulateRequest, SimulateResponse
from app.ml.train import MODEL_CAVEAT
from app.scenarios.cache import cache

router = APIRouter()


def _edge_geojson(road_graph, u, v) -> dict:
    return {
        "type": "LineString",
        "coordinates": [
            [road_graph.nodes[u]["lng"], road_graph.nodes[u]["lat"]],
            [road_graph.nodes[v]["lng"], road_graph.nodes[v]["lat"]],
        ],
    }


@router.post("/api/simulate", response_model=SimulateResponse)
def simulate(req: SimulateRequest) -> SimulateResponse:
    scenario = cache.compute_live(req.rainfall_intensity_mm_hr, req.duration_min)

    node_predictions = [
        NodePrediction(
            node_id=node_id,
            lat=cache.drainage_graph.nodes[node_id]["lat"],
            lng=cache.drainage_graph.nodes[node_id]["lng"],
            depth_m_mean=scenario.node_depth_mean[node_id],
            depth_m_std=scenario.node_depth_std[node_id],
        )
        for node_id in scenario.node_depth_mean
    ]

    road_segments = [
        RoadSegment(edge_id=data["edge_id"], state=data["state"], geometry=_edge_geojson(scenario.road_graph, u, v))
        for u, v, data in scenario.road_graph.edges(data=True)
    ]

    return SimulateResponse(
        scenario_id=scenario.scenario_id,
        node_predictions=node_predictions,
        road_segments=road_segments,
        model_caveat=MODEL_CAVEAT,
        is_synthetic_ward=scenario.is_synthetic_ward,
        at_risk_infra_ids=[r.infra_id for r in scenario.critical_access_risks],
    )
