"""Terrain derivatives from DEM tiles: mosaic -> UTM @30 m -> slope, local relative elevation.
Flow accumulation is deliberately NOT computed (needs hydrological conditioning)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
from rasterio.merge import merge
from rasterio.warp import Resampling, calculate_default_transform, reproject
from scipy.ndimage import uniform_filter


def mosaic_to_utm(tile_paths: list[Path], bounds_wgs84, utm_epsg: int, res: float = 30.0, pad: float = 0.02):
    w, s, e, n = bounds_wgs84
    dss = [rasterio.open(p) for p in tile_paths]
    try:
        arr, tr = merge(dss, bounds=(w - pad, s - pad, e + pad, n + pad), nodata=-9999.0, dtype="float32")
        src_crs, nodata = dss[0].crs, -9999.0
    finally:
        for d in dss:
            d.close()
    src = arr[0]
    h, wd = src.shape
    left, top = tr.c, tr.f
    right, bottom = left + tr.a * wd, top + tr.e * h
    dst_tr, dw, dh = calculate_default_transform(src_crs, f"EPSG:{utm_epsg}", wd, h, left, bottom, right, top, resolution=res)
    dst = np.full((dh, dw), np.nan, dtype="float32")
    src_nan = np.where(src == nodata, np.nan, src)
    reproject(src_nan, dst, src_transform=tr, src_crs=src_crs, dst_transform=dst_tr, dst_crs=f"EPSG:{utm_epsg}",
              resampling=Resampling.bilinear, src_nodata=np.nan, dst_nodata=np.nan)
    return dst, dst_tr


def slope_degrees(elev: np.ndarray, res: float) -> np.ndarray:
    gy, gx = np.gradient(elev, res)
    return np.degrees(np.arctan(np.hypot(gx, gy))).astype("float32")


def relative_elevation(elev: np.ndarray, res: float, radius_m: float = 500.0) -> np.ndarray:
    """Elevation minus mean elevation in a square window (2*radius+1). NaN-aware (normalised convolution)."""
    size = int(round(2 * radius_m / res)) + 1
    valid = np.isfinite(elev)
    num = uniform_filter(np.where(valid, elev, 0.0), size=size, mode="constant")
    den = uniform_filter(valid.astype("float64"), size=size, mode="constant")
    with np.errstate(invalid="ignore", divide="ignore"):
        local = np.where(den > 0.25, num / den, np.nan)
    return (elev - local).astype("float32")


def write_tif(path: Path, arr: np.ndarray, transform, epsg: int, description: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(path, "w", driver="GTiff", height=arr.shape[0], width=arr.shape[1], count=1, dtype="float32",
                       crs=f"EPSG:{epsg}", transform=transform, nodata=np.nan, compress="deflate") as d:
        d.write(arr.astype("float32"), 1)
        d.set_band_description(1, description)
