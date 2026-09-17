# Urban Flood Nowcasting System &middot; SIH26085

**Team Expecto Patronum** &middot; Smart India Hackathon 2026 &middot; Problem Statement
SIH26085 (Ministry of Earth Sciences / NCMRWF)

A real-time decision-support system that couples short-range rainfall
nowcasts with terrain, drainage-network behaviour, and road networks to
predict street-level flooding 1-3 hours ahead, then automatically reroutes
emergency vehicles around flooded roads -- with special priority given to
keeping routes open to hospitals, fire stations, and shelters.

This is **not** a rainfall heatmap. The full causal chain is implemented,
end to end, over one pilot ward:

```
Rainfall Nowcast -> Terrain/GIS -> SCS-CN Runoff -> Drainage Network Graph
  -> GNN Surrogate (with uncertainty) -> Water Depth & Flood Risk
  -> Flooded Road Detection -> Criticality-Weighted Emergency Rerouting
  -> Interactive Flood + Route Map
```

See `docs/ARCHITECTURE.md` for the full pipeline breakdown, `docs/DATA_SOURCES.md`
for exactly which numbers are real vs. synthetic, and `docs/DEMO_SCRIPT.md` for
a run-of-show.

## Honesty principles

- Nothing is fabricated: every dataset is either sourced from a real public
  API (documented) or clearly marked synthetic, in code and in the UI.
- The GNN is a surrogate for a simplified physics baseline, never claimed as
  a certified hydraulic model. Accuracy is reported against that baseline,
  not against unavailable real-world ground truth.
- See `docs/JUDGE_QA.md` for prepared, honest answers to the hard questions.

## Tech stack

- **Backend:** Python 3.11, FastAPI, SQLAlchemy + GeoAlchemy2 (PostGIS, with
  a SQLite zero-dependency fallback), WebSockets, Pydantic v2.
- **ML:** PyTorch + PyTorch Geometric, NumPy/Pandas/scikit-learn.
- **GIS:** geopandas, shapely, rasterio, pysheds, networkx, osmnx.
- **Frontend:** React 18 + TypeScript + Vite, MapLibre GL JS + Deck.gl,
  TailwindCSS, Zustand, Recharts.

## Quick start

### Option A -- Docker Compose (full stack, PostGIS)

```bash
docker-compose up
```

Backend: http://localhost:8000/docs &middot; Frontend: http://localhost:5173

### Option B -- Zero-dependency local dev (no Docker needed)

```bash
# Backend
cd backend
python -m venv .venv && source .venv/Scripts/activate   # or .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
python ../scripts/seed_synthetic_ward.py   # trains the GNN checkpoint once
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Copy `.env.example` to `backend/.env` first if you want to override any
default (rainfall thresholds, pipe diameters, etc). `DB_MODE=sqlite` (the
default) requires no PostGIS/Docker at all.

## Folder structure

```
sih-flood-nowcast/
├── docker-compose.yml
├── docs/                    ARCHITECTURE, DATA_SOURCES, DEMO_SCRIPT, JUDGE_QA
├── scripts/                 download_srtm.py, seed_synthetic_ward.py
├── backend/
│   └── app/
│       ├── core/            settings, db
│       ├── gis/             ward providers (synthetic + real), DEM, drainage graph
│       ├── hydrology/        SCS Curve Number
│       ├── ml/               features, physics baseline, GNN, train/infer/backtest
│       ├── routing/          road graph, router, criticality-weighted access
│       ├── scenarios/        pre-computed demo scenario cache
│       └── api/               FastAPI routes + schemas
└── frontend/
    └── src/
        ├── api/, store/       API client, Zustand store
        └── components/        MapView, panels, citizen alert view
```

## Screenshots / GIF

_Add a screenshot or short GIF of the dashboard here before submission --
`docs/DEMO_SCRIPT.md` beat 4 (the reroute comparison) is the strongest shot._

## Testing

```bash
cd backend
pytest --cov=app --cov-report=term-missing
```

## License

MIT (see `LICENSE`).
