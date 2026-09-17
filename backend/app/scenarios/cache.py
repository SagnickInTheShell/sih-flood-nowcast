"""Pre-computes & caches demo scenarios at startup so the live demo never
depends on slow real-time computation (§12).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.core.config import settings
from app.gis.drainage_graph import build_drainage_graph
from app.gis.real_ward import RealWardProvider
from app.gis.synthetic_ward import SyntheticWardProvider
from app.ml.features import assign_catchments, build_static_features
from app.ml.infer import load_model, predict_scenario
from app.routing.criticality import check_critical_access
from app.routing.road_graph import apply_flood_state, build_road_graph

PRESET_SCENARIOS = {
    "light": {"label": "Light shower", "rainfall_intensity_mm_hr": 20, "duration_min": 45},
    "moderate": {"label": "Moderate storm", "rainfall_intensity_mm_hr": 60, "duration_min": 90},
    "heavy": {"label": "Heavy cloudburst", "rainfall_intensity_mm_hr": 100, "duration_min": 120},
}


@dataclass
class CachedScenario:
    scenario_id: str
    label: str
    rainfall_intensity_mm_hr: float
    duration_min: float
    node_depth_mean: dict
    node_depth_std: dict
    road_graph: object
    critical_access_risks: list
    baseline_timeseries: object
    is_synthetic_ward: bool


class ScenarioCache:
    def __init__(self):
        self.provider = None
        self.drainage_graph = None
        self.static = None
        self.model = None
        self.model_loaded_from_checkpoint = False
        self.scenarios: dict[str, CachedScenario] = {}
        self.by_preset: dict[str, str] = {}

    def startup(self):
        self.provider = (
            SyntheticWardProvider() if settings.PILOT_MODE == "synthetic" else RealWardProvider()
        )
        self.drainage_graph = build_drainage_graph(self.provider)
        catchments = assign_catchments(self.provider, self.drainage_graph)
        self.static = build_static_features(self.drainage_graph, catchments)
        self.model, self.model_loaded_from_checkpoint = load_model()

        for key, cfg in PRESET_SCENARIOS.items():
            scenario = self._compute_scenario(
                cfg["label"], cfg["rainfall_intensity_mm_hr"], cfg["duration_min"]
            )
            self.scenarios[scenario.scenario_id] = scenario
            self.by_preset[key] = scenario.scenario_id

    def _compute_scenario(self, label, rainfall_intensity_mm_hr, duration_min) -> CachedScenario:
        prediction = predict_scenario(
            self.provider, self.drainage_graph, self.static, self.model,
            rainfall_intensity_mm_hr, duration_min,
        )
        node_depth_mean = dict(zip(prediction["node_order"], prediction["depth_mean"].tolist()))
        node_depth_std = dict(zip(prediction["node_order"], prediction["depth_std"].tolist()))

        road_graph = build_road_graph(self.provider)
        apply_flood_state(road_graph, self.drainage_graph, node_depth_mean)
        critical_infra = self.provider.get_critical_infrastructure()
        risks = check_critical_access(road_graph, critical_infra)

        return CachedScenario(
            scenario_id=f"sim_{uuid.uuid4().hex[:8]}",
            label=label,
            rainfall_intensity_mm_hr=rainfall_intensity_mm_hr,
            duration_min=duration_min,
            node_depth_mean=node_depth_mean,
            node_depth_std=node_depth_std,
            road_graph=road_graph,
            critical_access_risks=risks,
            baseline_timeseries=prediction["baseline_result"],
            is_synthetic_ward=self.provider.is_synthetic,
        )

    def compute_live(self, rainfall_intensity_mm_hr, duration_min, label="Custom") -> CachedScenario:
        scenario = self._compute_scenario(label, rainfall_intensity_mm_hr, duration_min)
        self.scenarios[scenario.scenario_id] = scenario
        return scenario

    def get(self, scenario_id: str) -> CachedScenario | None:
        return self.scenarios.get(scenario_id)


cache = ScenarioCache()
