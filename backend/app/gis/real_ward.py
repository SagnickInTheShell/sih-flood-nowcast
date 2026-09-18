"""Real-ward data provider: ingests an actual pilot ward via OpenStreetMap
(roads + waterways, through osmnx/Overpass) and a DEM tile.

Requires REAL_WARD_BBOX="min_lon,min_lat,max_lon,max_lat". The DEM is
fetched automatically on first use from AWS's public, keyless "terrarium"
elevation tiles (see terrain_tiles.py) -- no manual download needed. A
higher-resolution SRTM tile from USGS EarthExplorer (scripts/download_srtm.py)
can be dropped at the same path instead if you have one; this provider
doesn't care which source produced the GeoTIFF at self.dem_path.

Satisfies the same WardDataProvider interface as SyntheticWardProvider, so
the rest of the pipeline (hydrology -> drainage graph -> GNN -> routing)
needs zero changes to consume real data. The one seam that's genuinely
different from the synthetic path: every road-graph node here needs a
(grid_row, grid_col) pair locating it within the DEM raster, computed via
the DEM's affine transform, so downstream elevation sampling and catchment
assignment (written against a rectangular grid) work unmodified.
"""
from __future__ import annotations

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

    @lru_cache(maxsize=1)
    def _dem(self):
        if not self.dem_path.exists():
            from app.gis.terrain_tiles import fetch_dem_geotiff

            fetch_dem_geotiff(self.min_lon, self.min_lat, self.max_lon, self.max_lat, self.dem_path)

        import rasterio

        with rasterio.open(self.dem_path) as src:
            elevation = src.read(1).astype(float)
            transform = src.transform
        return elevation, transform

    def grid_resolution_m(self) -> float:
        # Derived from the DEM's own affine transform (degrees/pixel),
        # NOT settings.GRID_RESOLUTION_M -- that setting is specific to the
        # synthetic ward's hand-built grid, and would silently mis-size
        # every catchment area here if reused (terrarium-tile pixels are
        # ~9-10m at zoom 14, not the synthetic ward's 20m).
        _, transform = self._dem()
        mid_lat = (self.min_lat + self.max_lat) / 2
        meters_per_deg_lng = METERS_PER_DEG_LAT * np.cos(np.radians(mid_lat))
        px_w_m = abs(transform.a) * meters_per_deg_lng
        px_h_m = abs(transform.e) * METERS_PER_DEG_LAT
        return float((px_w_m + px_h_m) / 2)

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

    def _latlng_to_cell(self, lat: float, lng: float) -> tuple[float, float]:
        _, transform = self._dem()
        col, row = ~transform * (lng, lat)
        return (row, col)

    @lru_cache(maxsize=1)
    def _waterway_geometries(self):
        import osmnx as ox

        bbox = (self.min_lon, self.min_lat, self.max_lon, self.max_lat)
        try:
            waterways = ox.features_from_bbox(bbox=bbox, tags={"waterway": True})
        except Exception:
            return []
        return list(waterways.geometry) if not waterways.empty else []

    def _near_waterway(self, lat: float, lng: float, threshold_m: float = 120.0) -> bool:
        """True if (lat, lng) is within threshold_m of any mapped waterway.

        # ASSUMPTION: without curated municipal storm-drain records, a road
        # is treated as drain-carrying if it runs near a mapped waterway
        # (river/canal/lake edge) -- see docs/JUDGE_QA.md on why OSM
        # drainage data is otherwise too sparse to rely on directly.
        """
        from shapely.geometry import Point

        geometries = self._waterway_geometries()
        if not geometries:
            return False
        point = Point(lng, lat)
        meters_per_deg_lng = METERS_PER_DEG_LAT * np.cos(np.radians(lat))
        threshold_deg = threshold_m / max(METERS_PER_DEG_LAT, meters_per_deg_lng)
        return any(point.distance(geom) < threshold_deg for geom in geometries)

    @lru_cache(maxsize=1)
    def _road_graph(self) -> nx.Graph:
        import osmnx as ox

        # osmnx >= 2.0 API: bbox is (west, south, east, north).
        bbox = (self.min_lon, self.min_lat, self.max_lon, self.max_lat)
        g_osm = ox.graph_from_bbox(bbox=bbox, network_type="drive")

        g = nx.Graph()
        for node, data in g_osm.nodes(data=True):
            lat, lng = data["y"], data["x"]
            grid_row, grid_col = self._latlng_to_cell(lat, lng)
            g.add_node(
                str(node), lat=lat, lng=lng,
                grid_row=grid_row, grid_col=grid_col,
                is_major_junction=False,
            )
        for u, v, data in g_osm.edges(data=True):
            length_m = data.get("length", 0.0) or 1.0
            highway = data.get("highway", "")
            if isinstance(highway, list):
                highway = highway[0] if highway else ""
            is_arterial = highway in ("primary", "secondary", "trunk")
            mid_lat = (g.nodes[str(u)]["lat"] + g.nodes[str(v)]["lat"]) / 2
            mid_lng = (g.nodes[str(u)]["lng"] + g.nodes[str(v)]["lng"]) / 2
            has_drain = self._near_waterway(mid_lat, mid_lng)
            g.add_edge(str(u), str(v), length_m=length_m, is_arterial=is_arterial,
                       has_drain=has_drain, edge_id=f"r_{u}_{v}")
        return g

    def get_road_graph(self) -> nx.Graph:
        return self._road_graph().copy()

    def get_critical_infrastructure(self) -> list[CriticalInfra]:
        import osmnx as ox

        bbox = (self.min_lon, self.min_lat, self.max_lon, self.max_lat)
        tags = {"amenity": ["hospital", "fire_station"], "emergency": ["shelter"]}
        try:
            feats = ox.features_from_bbox(bbox=bbox, tags=tags)
        except Exception:
            return []
        out = []
        for idx, row in feats.iterrows():
            geom = row.geometry.centroid
            amenity = row.get("amenity") or row.get("emergency") or "unknown"
            infra_type = {
                "hospital": "hospital",
                "fire_station": "fire_station",
                "shelter": "shelter",
            }.get(amenity, "unknown")
            if infra_type == "unknown":
                continue
            # osmnx >= 2.0's features_from_bbox indexes by (osm_type, id);
            # flatten that tuple into a clean, stable string id.
            clean_id = "_".join(str(part) for part in idx) if isinstance(idx, tuple) else str(idx)
            name = row.get("name")
            if not isinstance(name, str) or not name:
                name = f"{infra_type}_{clean_id}"
            out.append(CriticalInfra(clean_id, infra_type, str(name), geom.y, geom.x))
        return out
