"""CRS helpers. All distance/area work happens in a projected UTM CRS, never in degrees."""
from __future__ import annotations

import geopandas as gpd
from shapely.geometry.base import BaseGeometry


def utm_epsg_for(lon: float, lat: float) -> int:
    zone = int((lon + 180) // 6) + 1
    return (32600 if lat >= 0 else 32700) + zone


def study_utm(gdf_wgs84: gpd.GeoDataFrame) -> int:
    c = gdf_wgs84.to_crs(4326).geometry.union_all().centroid
    return utm_epsg_for(c.x, c.y)


def to_wgs84(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    if gdf.crs is None:
        raise ValueError("GeoDataFrame has no CRS; refusing to guess")
    return gdf.to_crs(4326)
