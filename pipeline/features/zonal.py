"""Zonal statistics over polygons using exact polygon masks (not bbox approximations)."""
from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.mask import mask as rio_mask


def _vals(ds, geom, nodata_extra=None):
    try:
        arr, _ = rio_mask(ds, [geom], crop=True, filled=False, all_touched=False)
    except ValueError:  # polygon does not overlap raster
        return np.array([])
    a = arr[0]
    m = np.ma.getmaskarray(a)
    v = np.ma.getdata(a)[~m].astype("float64")
    return v[np.isfinite(v)]


def _geoms(ds, gdf):
    return gdf.to_crs(ds.crs).geometry


def zonal_mean(path, gdf, min_pixels: int = 1) -> pd.Series:
    with rasterio.open(path) as ds:
        out = [(_v.mean() if (_v := _vals(ds, g)).size >= min_pixels else np.nan) for g in _geoms(ds, gdf)]
    return pd.Series(out, index=gdf.index, dtype="float64")


def zonal_sum(path, gdf) -> pd.Series:
    """Sum of pixel values whose centres fall in the polygon. NaN (not 0) where no valid pixels."""
    with rasterio.open(path) as ds:
        out = [(_v.sum() if (_v := _vals(ds, g)).size else np.nan) for g in _geoms(ds, gdf)]
    return pd.Series(out, index=gdf.index, dtype="float64")


def zonal_class_share(path, gdf, codes, min_pixels: int = 1) -> pd.Series:
    with rasterio.open(path) as ds:
        out = []
        for g in _geoms(ds, gdf):
            v = _vals(ds, g)
            out.append(np.isin(v, list(codes)).mean() if v.size >= min_pixels else np.nan)
    return pd.Series(out, index=gdf.index, dtype="float64")
