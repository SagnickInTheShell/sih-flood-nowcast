from __future__ import annotations

from fastapi import APIRouter

from app.api.schemas import ScenarioSummary
from app.scenarios.cache import cache

router = APIRouter()


@router.get("/api/scenarios", response_model=list[ScenarioSummary])
def list_scenarios() -> list[ScenarioSummary]:
    return [
        ScenarioSummary(
            scenario_id=sid,
            label=cache.scenarios[sid].label,
            rainfall_intensity_mm_hr=cache.scenarios[sid].rainfall_intensity_mm_hr,
            duration_min=cache.scenarios[sid].duration_min,
        )
        for sid in cache.by_preset.values()
    ]
