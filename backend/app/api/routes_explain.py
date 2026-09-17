from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.ml.explain import explain_node
from app.ml.features import assign_catchments
from app.scenarios.cache import cache

router = APIRouter()


@router.get("/api/explain/{node_id}")
def explain(node_id: str, rainfall_intensity_mm_hr: float = 60, duration_min: float = 90) -> dict:
    if node_id not in cache.drainage_graph.nodes:
        raise HTTPException(status_code=404, detail=f"Unknown node_id '{node_id}'")
    catchments = assign_catchments(cache.provider, cache.drainage_graph)
    factors = explain_node(cache.drainage_graph, catchments, rainfall_intensity_mm_hr, duration_min, node_id)
    return {"node_id": node_id, "factors": factors}
