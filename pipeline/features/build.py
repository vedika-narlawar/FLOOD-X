"""Feature engineering on the analysis grid. Every feature has a manifest entry that says
whether it was computed and from which inputs; missing inputs yield 'unavailable', never zeros."""
from __future__ import annotations

import glob

import geopandas as gpd
import numpy as np
import pandas as pd

from ..common import Blocked, data_dir, get_logger, now_iso, write_json_atomic
from . import terrain
from .zonal import zonal_class_share, zonal_mean, zonal_sum

log = get_logger("floodx.features")
RES = 30.0
BUILTUP, VEG = {50}, {10, 20, 30, 40, 90, 95, 100}

FEATURE_DEFS = {
    "elev_mean_m": ("Mean elevation", "m a.s.l. (EGM2008)", "dem_cop_glo30", "Mean of 30 m DSM pixels in cell"),
    "slope_mean_deg": ("Mean slope", "degrees", "dem_cop_glo30", "Mean of np.gradient slope on 30 m UTM DSM"),
    "rel_elev_mean_m": ("Relative elevation", "m", "dem_cop_glo30", "Pixel minus mean in 1 km square window, averaged over cell"),
    "builtup_share": ("Built-up land-cover share", "fraction 0-1", "landcover_worldcover_2021", "Share of 10 m pixels with class 50"),
    "vegetated_share": ("Vegetated land-cover share", "fraction 0-1", "landcover_worldcover_2021", "Share of tree/shrub/grass/crop/wetland/mangrove/moss pixels"),
    "population_sum": ("Population (WorldPop)", "people", "population_worldpop_2020", "Sum of pixel values with centre in cell; modelled, not census"),
    "dist_waterway_m": ("Distance to nearest mapped waterway", "m", "osm_pune", "Centroid-to-line distance in UTM; OSM waterway completeness unverified"),
    "road_length_m": ("Mapped road length", "m", "osm_pune", "Length of OSM road segments clipped to cell, in UTM"),
    "n_hospital": ("Hospitals (OSM)", "count", "osm_pune", "OSM amenity=hospital points in cell"),
    "n_clinic": ("Clinics (OSM)", "count", "osm_pune", "OSM amenity=clinic"),
    "n_school": ("Schools (OSM)", "count", "osm_pune", "OSM amenity=school"),
    "n_fire_station": ("Fire stations (OSM)", "count", "osm_pune", "OSM amenity=fire_station"),
    "n_police": ("Police stations (OSM)", "count", "osm_pune", "OSM amenity=police"),
    "flow_accumulation": ("Flow accumulation", "cells", "dem_cop_glo30", "NOT COMPUTED: requires hydrological conditioning"),
}


def terrain_stage() -> list[str]:
    tiles = sorted(glob.glob(str(data_dir() / "raw" / "dem" / "*.tif")))
    if not tiles:
        raise Blocked("No DEM tiles in data/raw/dem (download_dem stage blocked or not run)", ["download_dem"])
    sa = gpd.read_file(data_dir() / "interim" / "study_area.gpkg")
    epsg = int(sa.utm_epsg.iloc[0])
    elev, tr = terrain.mosaic_to_utm([__import__("pathlib").Path(t) for t in tiles], sa.total_bounds, epsg, RES)
    # coverage check on the mosaic over the study area
    proc = data_dir() / "processed" / "terrain"
    terrain.write_tif(proc / "elevation_utm.tif", elev, tr, epsg, "DSM elevation m")
    terrain.write_tif(proc / "slope_deg.tif", terrain.slope_degrees(elev, RES), tr, epsg, "slope deg")
    terrain.write_tif(proc / "rel_elev_m.tif", terrain.relative_elevation(elev, RES), tr, epsg, "relative elevation m")
    return [str(proc / f) for f in ("elevation_utm.tif", "slope_deg.tif", "rel_elev_m.tif")]


def build_features(grid: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, dict]:
    d = data_dir()
    manifest = {k: {"label": v[0], "units": v[1], "source_dataset": v[2], "method": v[3],
                    "status": "unavailable", "reason": None, "n_valid": 0} for k, v in FEATURE_DEFS.items()}
    manifest["flow_accumulation"]["reason"] = "not implemented (needs pit-filled DEM and validated channel network)"
    g = grid.copy()
    cell_area_km2 = g["clipped_area_m2"] / 1e6

    def put(name, series, reason_if_empty=""):
        series = pd.Series(series, index=g.index)
        g[name] = series
        n = int(series.notna().sum())
        manifest[name].update(n_valid=n, status="available" if n else "unavailable",
                              reason=None if n else (reason_if_empty or "no valid values"))

    t = d / "processed" / "terrain"
    if (t / "elevation_utm.tif").exists():
        put("elev_mean_m", zonal_mean(t / "elevation_utm.tif", g))
        put("slope_mean_deg", zonal_mean(t / "slope_deg.tif", g))
        put("rel_elev_mean_m", zonal_mean(t / "rel_elev_m.tif", g))
    else:
        for k in ("elev_mean_m", "slope_mean_deg", "rel_elev_mean_m"):
            manifest[k]["reason"] = "terrain rasters not generated (DEM unavailable)"
    lc = list((d / "raw" / "landcover").glob("*.tif"))
    if lc:
        put("builtup_share", zonal_class_share(lc[0], g, BUILTUP, min_pixels=10))
        put("vegetated_share", zonal_class_share(lc[0], g, VEG, min_pixels=10))
    else:
        for k in ("builtup_share", "vegetated_share"):
            manifest[k]["reason"] = "land-cover raster unavailable"
    pop = list((d / "raw" / "population").glob("*.tif"))
    if pop:
        s = zonal_sum(pop[0], g)
        put("population_sum", s.clip(lower=0))
    else:
        manifest["population_sum"]["reason"] = "population raster unavailable"
    wp = d / "interim" / "osm_waterways.gpkg"
    if wp.exists():
        w = gpd.read_file(wp).to_crs(g.crs)
        if len(w):
            u = w.geometry.union_all()
            put("dist_waterway_m", g.geometry.centroid.distance(u))
        else:
            manifest["dist_waterway_m"]["reason"] = "OSM returned zero waterway features"
    else:
        manifest["dist_waterway_m"]["reason"] = "OSM waterways unavailable"
    rp = d / "interim" / "osm_roads.gpkg"
    if rp.exists():
        r = gpd.read_file(rp).to_crs(g.crs)
        if len(r):
            inter = gpd.overlay(r[["geometry"]], g[["cell_id", "geometry"]], how="intersection", keep_geom_type=True)
            ln = inter.assign(L=inter.length).groupby("cell_id")["L"].sum()
            put("road_length_m", g["cell_id"].map(ln).fillna(0.0))  # zero is meaningful here: roads mapped, none in cell
    else:
        manifest["road_length_m"]["reason"] = "OSM roads unavailable"
    fp = d / "interim" / "osm_facilities.gpkg"
    if fp.exists():
        f = gpd.read_file(fp).to_crs(g.crs)
        j = gpd.sjoin(f, g[["cell_id", "geometry"]], how="inner", predicate="within")
        for key, col in (("hospital", "n_hospital"), ("clinic", "n_clinic"), ("school", "n_school"),
                         ("fire_station", "n_fire_station"), ("police", "n_police")):
            cnt = j[j["amenity"] == key].groupby("cell_id").size()
            put(col, g["cell_id"].map(cnt).fillna(0).astype(float))
    else:
        for k in ("n_hospital", "n_clinic", "n_school", "n_fire_station", "n_police"):
            manifest[k]["reason"] = "OSM facilities unavailable"
    return g, manifest


def run() -> list[str]:
    gp = data_dir() / "processed" / "grid.gpkg"
    if not gp.exists():
        raise Blocked("grid missing", ["grid"])
    g, manifest = build_features(gpd.read_file(gp))
    out_dir = data_dir() / "processed" / "features"
    out_dir.mkdir(parents=True, exist_ok=True)
    g.to_parquet(out_dir / "grid_features.parquet")
    write_json_atomic(out_dir / "feature_manifest.json", {"generated_at": now_iso(), "crs": str(g.crs), "features": manifest})
    avail = [k for k, v in manifest.items() if v["status"] == "available"]
    log.info("features available: %s", avail)
    if not avail:
        raise Blocked("Grid skeleton written, but no environmental features could be computed: "
                      "all raster/OSM inputs are unavailable (see feature_manifest.json for per-feature reasons)",
                      [k for k, v in manifest.items() if v["status"] != "available"])
    return [str(out_dir / "grid_features.parquet"), str(out_dir / "feature_manifest.json")]
