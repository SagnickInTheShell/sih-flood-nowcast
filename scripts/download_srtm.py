#!/usr/bin/env python3
"""Instructions + helper for fetching a real SRTM DEM tile for PILOT_MODE=real.

SRTM tiles require a free USGS EarthExplorer account -- this script does
NOT attempt to scrape or bypass that login, per the project's data-honesty
principles. It prints exact manual steps and where to save the result so
app/gis/real_ward.py can find it.

Usage:
    python scripts/download_srtm.py --bbox min_lon,min_lat,max_lon,max_lat
"""
from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bbox", required=True,
        help="min_lon,min_lat,max_lon,max_lat (same value as REAL_WARD_BBOX in .env)",
    )
    parser.add_argument(
        "--out", default="./backend/data/real_ward_dem.tif",
        help="Where to save the downloaded GeoTIFF (default: ./backend/data/real_ward_dem.tif)",
    )
    args = parser.parse_args()
    min_lon, min_lat, max_lon, max_lat = (float(x) for x in args.bbox.split(","))

    print(
        f"""
SRTM DEM download -- manual steps (requires a free USGS EarthExplorer account)
================================================================================
1. Create a free account at https://ers.cr.usgs.gov/register/ if you don't
   have one already.
2. Go to https://earthexplorer.usgs.gov/ and sign in.
3. Under "Search Criteria" > "Polygon", enter this bounding box (or draw it
   on the map): min_lon={min_lon}, min_lat={min_lat}, max_lon={max_lon}, max_lat={max_lat}
4. Under "Data Sets", select: Digital Elevation > SRTM > SRTM 1 Arc-Second
   Global (30m resolution, ~90m also acceptable if 30m is unavailable for
   your area).
5. Click "Results", download the GeoTIFF for the tile(s) covering your bbox.
6. If your bbox spans multiple SRTM tiles, mosaic them first, e.g.:
       gdal_merge.py -o {args.out} tile1.tif tile2.tif ...
7. Save (or move) the final GeoTIFF to: {args.out}
8. Set PILOT_MODE=real and REAL_WARD_BBOX={min_lon},{min_lat},{max_lon},{max_lat}
   in your .env file.

app/gis/real_ward.py reads the DEM from that exact path via rasterio, and
app/gis/dem.py's load_and_process_raster() processes it with pysheds.
"""
    )


if __name__ == "__main__":
    main()
