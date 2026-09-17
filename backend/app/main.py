"""FastAPI application entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    routes_backtest,
    routes_explain,
    routes_infra,
    routes_route,
    routes_scenarios,
    routes_simulate,
    ws_live,
)
from app.core.config import settings
from app.scenarios.cache import cache

@asynccontextmanager
async def lifespan(app: FastAPI):
    cache.startup()
    yield


app = FastAPI(
    title="SIH26085 Urban Flood Nowcasting System",
    description=(
        "Rainfall nowcast -> terrain/GIS -> SCS-CN runoff -> drainage graph -> "
        "GNN surrogate (with uncertainty) -> flooded-road detection -> "
        "criticality-weighted emergency rerouting."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_simulate.router)
app.include_router(routes_scenarios.router)
app.include_router(routes_route.router)
app.include_router(routes_infra.router)
app.include_router(routes_backtest.router)
app.include_router(routes_explain.router)
app.include_router(ws_live.router)


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "pilot_mode": settings.PILOT_MODE,
        "model_checkpoint_loaded": cache.model_loaded_from_checkpoint,
    }
