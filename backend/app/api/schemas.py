"""Pydantic v2 request/response models matching the API contract in §7."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class SimulateRequest(BaseModel):
    rainfall_intensity_mm_hr: float
    duration_min: float


class NodePrediction(BaseModel):
    node_id: str
    lat: float
    lng: float
    depth_m_mean: float
    depth_m_std: float


class RoadSegment(BaseModel):
    edge_id: str
    state: Literal["clear", "at_risk", "flooded"]
    geometry: dict[str, Any]


class SimulateResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    scenario_id: str
    node_predictions: list[NodePrediction]
    road_segments: list[RoadSegment]
    model_caveat: str
    is_synthetic_ward: bool


class LatLng(BaseModel):
    lat: float
    lng: float


class RouteRequest(BaseModel):
    start: LatLng
    end: LatLng
    scenario_id: str
    algorithm: Literal["astar", "dijkstra"] = "astar"


class CriticalAccessRiskSchema(BaseModel):
    infra_id: str
    infra_type: str
    infra_name: str
    access_redundancy_score: int
    message: str


class RouteResponse(BaseModel):
    route_geometry: dict[str, Any]
    eta_seconds: float
    avoided_flooded_segments: list[str]
    baseline_route_geometry: dict[str, Any]
    baseline_eta_seconds: float
    critical_access_risk: CriticalAccessRiskSchema | None = None


class CriticalInfraSchema(BaseModel):
    infra_id: str
    infra_type: str
    name: str
    lat: float
    lng: float


class ScenarioSummary(BaseModel):
    scenario_id: str
    label: str
    rainfall_intensity_mm_hr: float
    duration_min: float
