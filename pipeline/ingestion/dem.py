"""Copernicus DEM GLO-30 tiles covering the Pune study area (COG, public AWS bucket)."""
from __future__ import annotations

import math

from ..common import data_dir, download_file, get_logger
from ._raster_common import finish_raster_dataset, study_bounds_wgs84

log = get_logger("floodx.dem")
BASE = "https://copernicus-dem-30m.s3.amazonaws.com"


def tile_names(bounds) -> list[str]:
    w, s, e, n = bounds
    names = []
    for lat in range(math.floor(s), math.floor(n) + 1):
        for lon in range(math.floor(w), math.floor(e) + 1):
            ns = f"N{lat:02d}" if lat >= 0 else f"S{-lat:02d}"
            ew = f"E{lon:03d}" if lon >= 0 else f"W{-lon:03d}"
            names.append(f"Copernicus_DSM_COG_10_{ns}_00_{ew}_00_DEM")
    return names


def run(force: bool = False) -> list[str]:
    outs = []
    for t in tile_names(study_bounds_wgs84()):
        dest = data_dir() / "raw" / "dem" / f"{t}.tif"
        info = download_file(f"{BASE}/{t}/{t}.tif", dest, min_bytes=1_000_000, force=force)
        outs.append(str(dest))
        log.info("DEM tile %s: %s bytes", t, info["bytes"])
    # validate each tile is readable; coverage is checked on the mosaic in the terrain stage
    import rasterio
    for p in outs:
        with rasterio.open(p) as ds:
            assert ds.crs is not None and ds.count == 1
    from .. import registry
    registry.update("dem_cop_glo30", status="parsed", local_path=str(data_dir() / "raw" / "dem"),
                    retrieval={"state": "ok", "tiles": outs}, parse={"state": "ok", "tiles": len(outs)},
                    history=f"downloaded and opened {len(outs)} tiles; mosaic coverage validated in terrain stage")
    return outs
