"""Vector validation. Returns a structured report; never mutates silently."""
from __future__ import annotations

import geopandas as gpd

from ..registry import PUNE_BBOX


def validate_vector(gdf: gpd.GeoDataFrame, *, expect_min: int = 1, expect_geom: tuple[str, ...] | None = None,
                    bbox: tuple[float, float, float, float] = PUNE_BBOX) -> dict:
    checks, ok = [], True

    def add(name, passed, detail=""):
        nonlocal ok
        ok &= bool(passed)
        checks.append({"check": name, "passed": bool(passed), "detail": str(detail)})

    add("has_crs", gdf.crs is not None, gdf.crs)
    add("min_feature_count", len(gdf) >= expect_min, f"{len(gdf)} features (min {expect_min})")
    add("no_empty_geometry", not gdf.geometry.is_empty.any(), int(gdf.geometry.is_empty.sum()))
    add("no_null_geometry", not gdf.geometry.isna().any(), int(gdf.geometry.isna().sum()))
    add("valid_geometry", gdf.geometry.is_valid.all(), f"{int((~gdf.geometry.is_valid).sum())} invalid")
    if expect_geom:
        bad = ~gdf.geom_type.isin(expect_geom)
        add("geometry_types", not bad.any(), sorted(gdf.geom_type.unique().tolist()))
    dups = int(gdf.geometry.to_wkb().duplicated().sum())
    add("no_duplicate_geometries", dups == 0, f"{dups} duplicates")
    if gdf.crs is not None and len(gdf):
        b = gdf.to_crs(4326).total_bounds
        inside = b[0] >= bbox[0] and b[1] >= bbox[1] and b[2] <= bbox[2] and b[3] <= bbox[3]
        add("within_pune_window", inside, [round(float(x), 4) for x in b])
    return {"passed": ok, "checks": checks, "feature_count": int(len(gdf))}


def repair_geometries(gdf: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, int]:
    """Explicit repair (make_valid) with a count, so repairs are logged not hidden."""
    from shapely import make_valid
    bad = ~gdf.geometry.is_valid
    n = int(bad.sum())
    if n:
        gdf = gdf.copy()
        gdf.loc[bad, "geometry"] = gdf.loc[bad, "geometry"].apply(make_valid)
    return gdf, n
