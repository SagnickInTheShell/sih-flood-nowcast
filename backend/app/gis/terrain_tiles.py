"""Automated, keyless DEM fetch for PILOT_MODE=real, using AWS's public
"Terrarium" elevation tile service (s3://elevation-tiles-prod, mirrored at
https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png).

# ASSUMPTION: scripts/download_srtm.py documents the "real" SRTM path via
# USGS EarthExplorer, which needs a free account and a manual browser
# session -- not something this backend can do for you automatically. This
# module is the automated alternative: the terrarium tiles are themselves
# derived from SRTM (plus other sources) by Mapzen/AWS and are public,
# no-signup data, so PILOT_MODE=real can fetch real elevation data on
# first boot with zero manual steps. Resolution is coarser than a raw
# SRTM tile (~9-10m/pixel at zoom 14 near the equator vs SRTM's native
# ~30m -- actually finer here, since terrarium tiles are resampled), but
# it is still real, sourced terrain data, not synthetic.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np

TILE_SIZE = 256


def _deg2num(lat_deg: float, lon_deg: float, zoom: int) -> tuple[int, int]:
    lat_rad = math.radians(lat_deg)
    n = 2.0**zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return xtile, ytile


def _num2deg(xtile: float, ytile: float, zoom: int) -> tuple[float, float]:
    n = 2.0**zoom
    lon_deg = xtile / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
    lat_deg = math.degrees(lat_rad)
    return lat_deg, lon_deg


def _decode_terrarium(png_array: np.ndarray) -> np.ndarray:
    """Terrarium encoding: elevation_m = (R * 256 + G + B / 256) - 32768."""
    r = png_array[:, :, 0].astype(np.float64)
    g = png_array[:, :, 1].astype(np.float64)
    b = png_array[:, :, 2].astype(np.float64)
    return (r * 256 + g + b / 256) - 32768


def fetch_dem_geotiff(
    min_lon: float, min_lat: float, max_lon: float, max_lat: float,
    out_path: str | Path, zoom: int = 14,
) -> Path:
    """Fetches, mosaics, crops, and writes a real elevation GeoTIFF for the
    given bbox using AWS's public terrarium tiles. Returns the written path.
    """
    import imageio.v3 as iio
    import rasterio
    import requests
    from rasterio.transform import Affine

    x0, y0 = _deg2num(max_lat, min_lon, zoom)  # NW corner tile
    x1, y1 = _deg2num(min_lat, max_lon, zoom)  # SE corner tile
    x0, x1 = min(x0, x1), max(x0, x1)
    y0, y1 = min(y0, y1), max(y0, y1)

    n_tiles_x = x1 - x0 + 1
    n_tiles_y = y1 - y0 + 1
    mosaic = np.zeros((n_tiles_y * TILE_SIZE, n_tiles_x * TILE_SIZE), dtype=np.float64)

    for ty in range(y0, y1 + 1):
        for tx in range(x0, x1 + 1):
            url = f"https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{zoom}/{tx}/{ty}.png"
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            tile_img = iio.imread(resp.content, extension=".png")
            elevation_tile = _decode_terrarium(tile_img)
            row0 = (ty - y0) * TILE_SIZE
            col0 = (tx - x0) * TILE_SIZE
            mosaic[row0:row0 + TILE_SIZE, col0:col0 + TILE_SIZE] = elevation_tile

    # Affine transform of the full mosaic (top-left of tile (x0,y0) to
    # bottom-right of tile (x1,y1)).
    lat_top, lon_left = _num2deg(x0, y0, zoom)
    lat_bottom, lon_right = _num2deg(x1 + 1, y1 + 1, zoom)
    px_w = (lon_right - lon_left) / mosaic.shape[1]
    px_h = (lat_top - lat_bottom) / mosaic.shape[0]
    mosaic_transform = Affine(px_w, 0.0, lon_left, 0.0, -px_h, lat_top)

    # Crop to the exact requested bbox.
    inv = ~mosaic_transform
    col_min, row_max = inv * (min_lon, min_lat)
    col_max, row_min = inv * (max_lon, max_lat)
    row_min, row_max = int(max(row_min, 0)), int(min(row_max, mosaic.shape[0]))
    col_min, col_max = int(max(col_min, 0)), int(min(col_max, mosaic.shape[1]))
    cropped = mosaic[row_min:row_max, col_min:col_max]

    crop_lon_left, crop_lat_top = mosaic_transform * (col_min, row_min)
    crop_transform = Affine(px_w, 0.0, crop_lon_left, 0.0, -px_h, crop_lat_top)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(
        out_path, "w", driver="GTiff",
        height=cropped.shape[0], width=cropped.shape[1], count=1,
        dtype=cropped.dtype, crs="EPSG:4326", transform=crop_transform,
    ) as dst:
        dst.write(cropped, 1)

    return out_path
