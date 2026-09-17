from __future__ import annotations

from fastapi import APIRouter

from app.api.schemas import CriticalInfraSchema
from app.scenarios.cache import cache

router = APIRouter()


@router.get("/api/critical-infrastructure", response_model=list[CriticalInfraSchema])
def critical_infrastructure() -> list[CriticalInfraSchema]:
    return [
        CriticalInfraSchema(infra_id=i.infra_id, infra_type=i.infra_type, name=i.name, lat=i.lat, lng=i.lng)
        for i in cache.provider.get_critical_infrastructure()
    ]
