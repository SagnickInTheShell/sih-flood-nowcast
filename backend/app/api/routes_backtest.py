from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/api/backtest/{event_id}")
def get_backtest(event_id: str) -> JSONResponse:
    return JSONResponse(
        status_code=501,
        content={"message": "No historical event configured yet. See docs/DATA_SOURCES.md for how to add one."},
    )
