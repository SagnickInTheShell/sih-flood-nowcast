from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.schemas import CriticalAccessRiskSchema, RouteRequest, RouteResponse
from app.routing.road_graph import build_road_graph
from app.routing.router import (
    nearest_node,
    path_edge_ids,
    path_flooded_segments,
    path_to_geojson_linestring,
    shortest_path_astar,
    shortest_path_dijkstra,
)
from app.scenarios.cache import cache

router = APIRouter()


@router.post("/api/route", response_model=RouteResponse)
def route(req: RouteRequest) -> RouteResponse:
    scenario = cache.get(req.scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail=f"Unknown scenario_id '{req.scenario_id}'")

    flood_graph = scenario.road_graph
    baseline_graph = build_road_graph(cache.provider)  # all-clear, unflood-aware

    start_node = nearest_node(flood_graph, req.start.lat, req.start.lng)
    end_node = nearest_node(flood_graph, req.end.lat, req.end.lng)

    solve = shortest_path_astar if req.algorithm == "astar" else shortest_path_dijkstra

    route_path, route_cost = solve(flood_graph, start_node, end_node)
    baseline_path, baseline_cost = solve(baseline_graph, start_node, end_node)

    route_edges = set(path_edge_ids(flood_graph, route_path))
    baseline_flooded_segments = path_flooded_segments(flood_graph, baseline_path)
    avoided = [e for e in baseline_flooded_segments if e not in route_edges]

    critical_risk = None
    for risk in scenario.critical_access_risks:
        infra = next(
            (i for i in cache.provider.get_critical_infrastructure() if i.infra_id == risk.infra_id),
            None,
        )
        if infra and abs(infra.lat - req.end.lat) < 0.002 and abs(infra.lng - req.end.lng) < 0.002:
            critical_risk = CriticalAccessRiskSchema(
                infra_id=risk.infra_id,
                infra_type=risk.infra_type,
                infra_name=risk.infra_name,
                access_redundancy_score=risk.access_redundancy_score,
                message=risk.message,
            )
            break

    return RouteResponse(
        route_geometry=path_to_geojson_linestring(flood_graph, route_path),
        eta_seconds=route_cost,
        avoided_flooded_segments=avoided,
        baseline_route_geometry=path_to_geojson_linestring(baseline_graph, baseline_path),
        baseline_eta_seconds=baseline_cost,
        critical_access_risk=critical_risk,
    )
