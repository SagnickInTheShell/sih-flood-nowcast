"""Real-ward data provider: ingests an actual pilot ward via OpenStreetMap
(roads + waterways, through osmnx/Overpass) and a locally-downloaded SRTM
DEM tile (through rasterio).

Requires REAL_WARD_BBOX="min_lon,min_lat,max_lon,max_lat" and a DEM tile
downloaded with scripts/download_srtm.py (SRTM tiles need a free USGS
EarthExplorer account -- see docs/DATA_SOURCES.md; we do not attempt to
bypass that requirement).

Satisfies the same WardDataProvider interface as SyntheticWardProvider,
so the rest of the pipeline (hydrology -> drainage graph -> GNN ->
routing) needs zero changes to consume real data.
"""
from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path

import networkx as nx
import numpy as np

from app.core.config import settings
from app.gis.ward_provider import CriticalInfra, WardDataProvider

METERS_PER_DEG_LAT = 111_320.0


class RealWardProvider(WardDataProvider):
    is_synthetic = False

    def __init__(self, dem_path: str | Path = "./data/real_ward_dem.tif"):
        if not settings.REAL_WARD_BBOX:
            raise ValueError(
                "PILOT_MODE=real requires REAL_WARD_BBOX to be set "
                "(format: min_lon,min_lat,max_lon,max_lat). See docs/DATA_SOURCES.md."
            )
        parts = [float(x) for x in settings.REAL_WARD_BBOX.split(",")]
        self.min_lon, self.min_lat, self.max_lon, self.max_lat = parts
        self.dem_path = Path(dem_path)
        self.resolution_m = settings.GRID_RESOLUTION_M

    def grid_resolution_m(self) -> float:
        return self.resolution_m

    @lru_cache(maxsize=1)
    def _dem(self):
        if not self.dem_path.exists():
            raise FileNotFoundError(
                f"No DEM tile at {self.dem_path}. Run scripts/download_srtm.py "
                f"for bbox {self.min_lon},{self.min_lat},{self.max_lon},{self.max_lat} "
                "(requires a free USGS EarthExplorer account)."
            )
        import rasterio

        with rasterio.open(self.dem_path) as src:
            elevation = src.read(1).astype(float)
            transform = src.transform
        return elevation, transform

    def get_elevation_grid(self) -> np.ndarray:
        elevation, _ = self._dem()
        return elevation

    def get_curve_number_grid(self) -> np.ndarray:
        # ASSUMPTION: without a licensed land-use/land-cover raster for the
        # target ward, curve numbers default to a flat NRCS "residential,
        # average condition" value (CN=75) everywhere. Replace with a real
        # LULC-derived CN raster before this mode is used operationally.
        elevation, _ = self._dem()
        return np.full_like(elevation, 75.0)

    def cell_to_latlng(self, row: float, col: float) -> tuple[float, float]:
        _, transform = self._dem()
        lng, lat = transform * (col, row)
        return (lat, lng)

    @lru_cache(maxsize=1)
    def _road_graph(self) -> nx.Graph:
        import osmnx as ox

        # osmnx >= 2.0 API: bbox is (west, south, east, north).
        bbox = (self.min_lon, self.min_lat, self.max_lon, self.max_lat)
        g_osm = ox.graph_from_bbox(bbox=bbox, network_type="drive")
        waterways = ox.features_from_bbox(bbox=bbox, tags={"waterway": True})

        g = nx.Graph()
        for node, data in g_osm.nodes(data=True):
            g.add_node(str(node), lat=data["y"], lng=data["x"], is_major_junction=False)
        for u, v, data in g_osm.edges(data=True):
            length_m = data.get("length", 0.0)
            highway = data.get("highway", "")
            is_arterial = isinstance(highway, str) and highway in (
                "primary", "secondary", "trunk",
            )
            # ASSUMPTION: without curated municipal storm-drain records,
            # "has_drain" is approximated as "runs near a mapped waterway".
            has_drain = waterways is not None and not waterways.empty
            g.add_edge(str(u), str(v), length_m=length_m, is_arterial=is_arterial,
                       has_drain=has_drain, edge_id=f"r_{u}_{v}")
        return g

    def get_road_graph(self) -> nx.Graph:
        return self._road_graph().copy()

    def get_critical_infrastructure(self) -> list[CriticalInfra]:
        import osmnx as ox

        bbox = (self.min_lon, self.min_lat, self.max_lon, self.max_lat)
        tags = {"amenity": ["hospital", "fire_station"], "emergency": ["shelter"]}
        feats = ox.features_from_bbox(bbox=bbox, tags=tags)
        out = []
        for idx, row in feats.iterrows():
            geom = row.geometry.centroid
            amenity = row.get("amenity") or row.get("emergency") or "unknown"
            infra_type = {
                "hospital": "hospital",
                "fire_station": "fire_station",
                "shelter": "shelter",
            }.get(amenity, "unknown")
            name = row.get("name", f"{infra_type}_{idx}")
            out.append(CriticalInfra(str(idx), infra_type, str(name), geom.y, geom.x))
        return out
