"""Regular analysis grid in UTM. Cell size is a documented, configurable choice (default 500 m),
matched to the ~30 m DEM and 100 m population rasters, NOT to the 10 m land-cover resolution."""
from __future__ import annotations

import geopandas as gpd
import numpy as np
from shapely.geometry import box

from ..common import Blocked, data_dir, get_logger

log = get_logger("floodx.grid")
MIN_FRAC = 0.10


def make_grid(study_utm: gpd.GeoDataFrame, wards_utm: gpd.GeoDataFrame, cell_m: float = 500.0) -> gpd.GeoDataFrame:
    poly = study_utm.geometry.union_all()
    minx, miny, maxx, maxy = poly.bounds
    minx, miny = np.floor(minx / cell_m) * cell_m, np.floor(miny / cell_m) * cell_m
    xs, ys = np.arange(minx, maxx, cell_m), np.arange(miny, maxy, cell_m)
    cells = [box(x, y, x + cell_m, y + cell_m) for x in xs for y in ys]
    g = gpd.GeoDataFrame(geometry=cells, crs=study_utm.crs)
    g = g[g.intersects(poly)].copy()
    g["geometry"] = g.geometry.intersection(poly)
    g = g[~g.geometry.is_empty]
    g["clipped_area_m2"] = g.area
    g = g[g["clipped_area_m2"] >= MIN_FRAC * cell_m**2].reset_index(drop=True)
    g.insert(0, "cell_id", [f"c{cell_m:.0f}_{i:05d}" for i in range(len(g))])
    # ward assignment by representative point (documented approximation)
    pts = g.copy()
    pts["geometry"] = g.geometry.representative_point()
    j = gpd.sjoin(pts, wards_utm[["ward_id", "ward_name", "geometry"]], how="left", predicate="within")
    j = j[~j.index.duplicated(keep="first")]
    g["ward_id"], g["ward_name"] = j["ward_id"].values, j["ward_name"].values
    g.attrs["cell_m"] = cell_m
    return g


def run(cell_m: float = 500.0) -> list[str]:
    sa_p, w_p = data_dir() / "interim" / "study_area.gpkg", data_dir() / "interim" / "boundaries_pmc_wards_2022.gpkg"
    if not (sa_p.exists() and w_p.exists()):
        raise Blocked("study area / wards missing", ["study_area"])
    sa = gpd.read_file(sa_p)
    epsg = int(sa.utm_epsg.iloc[0])
    wards = gpd.read_file(w_p).to_crs(epsg)
    wards["ward_id"] = wards["wardnum"].astype(int)
    wards["ward_name"] = wards["Name1"].astype(str)
    wards["municipality"] = "PMC"
    pc = data_dir() / "interim" / "boundaries_pcmc_wards.gpkg"
    if pc.exists():  # PCMC ids offset by 1000 so they never collide with PMC ward numbers
        import pandas as pd
        p2 = gpd.read_file(pc).to_crs(epsg)
        num = pd.to_numeric(p2["wardnum"], errors="coerce")
        p2["ward_id"] = (1000 + num.fillna(pd.Series(range(1, len(p2) + 1), index=p2.index))).astype(int)
        p2["ward_name"] = "PCMC: " + p2["name"].astype(str)
        p2["municipality"] = "PCMC"
        wards = pd.concat([wards[["ward_id", "ward_name", "municipality", "geometry"]],
                           p2[["ward_id", "ward_name", "municipality", "geometry"]]], ignore_index=True)
        wards = gpd.GeoDataFrame(wards, crs=epsg)
    wards.to_file(data_dir() / "interim" / "wards_utm.gpkg", driver="GPKG")
    g = make_grid(sa.to_crs(epsg), wards, cell_m)
    out = data_dir() / "processed" / "grid.gpkg"
    out.parent.mkdir(parents=True, exist_ok=True)
    g.to_file(out, driver="GPKG")
    log.info("grid: %d cells @ %.0f m in EPSG:%d; %d unassigned to ward", len(g), cell_m, epsg, int(g.ward_id.isna().sum()))
    return [str(out)]
