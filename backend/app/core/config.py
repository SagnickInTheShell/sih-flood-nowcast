"""Central application settings, read from environment / .env.

Every tunable referenced by the build spec lives here so nothing is a
magic number buried in a module.
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Pilot ward mode
    PILOT_MODE: str = "synthetic"  # "synthetic" | "real"
    REAL_WARD_BBOX: str = ""  # "min_lon,min_lat,max_lon,max_lat"

    # Database
    DB_MODE: str = "sqlite"  # "sqlite" | "postgis"
    DATABASE_URL: str = "sqlite:///./flood_nowcast.db"
    POSTGIS_URL: str = "postgresql+psycopg2://flood:flood@localhost:5432/flood_nowcast"

    # Synthetic ward generation
    SYNTHETIC_SEED: int = 42
    GRID_SIZE_CELLS: int = 100
    GRID_RESOLUTION_M: int = 20
    ANCHOR_LAT: float = 12.9716
    ANCHOR_LNG: float = 77.5946

    # Drainage network assumptions
    # ASSUMPTION: pipe diameters are not measured for any real ward; they are
    # plausible defaults for residential vs. arterial storm drains in a
    # planned layout, configurable per §6.3 of the spec.
    DRAIN_DIAMETER_RESIDENTIAL_MM: int = 450
    DRAIN_DIAMETER_ARTERIAL_MM: int = 900
    MANNINGS_N_CONCRETE: float = 0.013

    # Hydrology (SCS-CN)
    IA_COEFFICIENT: float = 0.2

    # Road / flood state thresholds (metres of predicted depth)
    DEPTH_THRESHOLD_AT_RISK_M: float = 0.15
    DEPTH_THRESHOLD_FLOODED_M: float = 0.30

    # ML
    MODEL_CHECKPOINT_PATH: str = "./app/ml/checkpoints/gnn_surrogate.pt"
    MC_DROPOUT_SAMPLES: int = 20

    # API
    CORS_ORIGINS: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
