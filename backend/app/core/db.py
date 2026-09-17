"""DB engine setup.

DB_MODE=sqlite gives a zero-dependency local dev path (no PostGIS
required) per §9 of the build spec. DB_MODE=postgis is used inside
docker-compose. The application's own graph/ward state lives in an
in-memory module-level cache (see app/scenarios/cache.py) regardless of
DB_MODE -- the SQL database here is only used for anything that needs
row-based persistence (currently: none is required for the prototype,
the engine is provided so the architecture is ready for it).
"""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


def _make_engine():
    if settings.DB_MODE == "postgis":
        return create_engine(settings.POSTGIS_URL, pool_pre_ping=True)
    # SQLite fallback -- no PostGIS extension available, geometry columns
    # are stored as GeoJSON text instead wherever the app touches SQL.
    return create_engine(
        settings.DATABASE_URL, connect_args={"check_same_thread": False}
    )


engine = _make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
