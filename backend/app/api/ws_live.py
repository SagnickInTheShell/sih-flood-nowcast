"""WS /ws/live?scenario_id=... streams the scenario's precomputed rainfall
timeseries, one message every 2 seconds (§7)."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.config import settings
from app.scenarios.cache import cache

router = APIRouter()


@router.websocket("/ws/live")
async def live(websocket: WebSocket) -> None:
    await websocket.accept()
    scenario_id = websocket.query_params.get("scenario_id")
    scenario = cache.get(scenario_id) if scenario_id else None
    if scenario is None:
        await websocket.send_json({"error": f"Unknown scenario_id '{scenario_id}'"})
        await websocket.close()
        return

    timeseries = scenario.baseline_timeseries
    try:
        for i, t_min in enumerate(timeseries.time_min):
            rainfall_mm_hr = scenario.rainfall_intensity_mm_hr if t_min <= scenario.duration_min else 0.0
            node_depths = {n: series[i] for n, series in timeseries.node_depth_timeseries.items()}

            flooded_edge_ids, at_risk_edge_ids = [], []
            for _u, _v, data in scenario.road_graph.edges(data=True):
                depth = node_depths.get(data.get("nearest_drainage_node"), 0.0)
                if depth >= settings.DEPTH_THRESHOLD_FLOODED_M:
                    flooded_edge_ids.append(data["edge_id"])
                elif depth >= settings.DEPTH_THRESHOLD_AT_RISK_M:
                    at_risk_edge_ids.append(data["edge_id"])

            await websocket.send_json({
                "t_min": t_min,
                "rainfall_mm_hr": rainfall_mm_hr,
                "node_depths": node_depths,
                "flooded_edge_ids": flooded_edge_ids,
                "at_risk_edge_ids": at_risk_edge_ids,
            })
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        pass
