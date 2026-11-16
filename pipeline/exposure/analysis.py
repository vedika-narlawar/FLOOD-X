"""Exposure of facilities, roads and population to susceptibility categories ('potentially
exposed to susceptibility' - not flooded, not damaged)."""
from __future__ import annotations

import geopandas as gpd
import pandas as pd

from ..common import Blocked, art_dir, data_dir, get_logger, now_iso, write_json_atomic

log = get_logger("floodx.exposure")
CATS = ["Very low", "Low", "Moderate", "High", "Very high"]
# Only these columns are facility counts. Other n_* columns (e.g. n_inputs_used) are NOT facilities.
FACILITY_COLS = ("n_hospital", "n_clinic", "n_school", "n_fire_station", "n_police")
CAVEAT = ("Located in a relatively higher-susceptibility cell != flooded. OSM and WorldPop completeness/accuracy are limited. "
          "Exposure is not predicted damage or loss.")


def summarise(grid: gpd.GeoDataFrame, facilities: gpd.GeoDataFrame | None) -> dict:
    g = grid.dropna(subset=["score"])
    res = {"generated_at": now_iso(), "caveat": CAVEAT, "categories": CATS, "sections": {}}
    # facilities
    cols = [c for c in FACILITY_COLS if c in g.columns and g[c].notna().any()]
    if cols:
        t = g.groupby("category")[cols].sum().reindex(CATS).fillna(0).astype(int)
        res["sections"]["facilities"] = {"status": "available", "by_category": t.to_dict(orient="index"),
                                         "note": "OSM-mapped facilities only; not a verified inventory"}
    else:
        res["sections"]["facilities"] = {"status": "unavailable", "reason": "OSM facility counts are not available in the feature grid"}
    if "road_length_m" in g.columns and g["road_length_m"].notna().any():
        t = (g.groupby("category")["road_length_m"].sum().reindex(CATS).fillna(0) / 1000).round(2)
        res["sections"]["roads"] = {"status": "available", "unit": "km", "by_category": t.to_dict()}
    else:
        res["sections"]["roads"] = {"status": "unavailable", "reason": "OSM road layer not available"}
    if "population_sum" in g.columns and g["population_sum"].notna().any():
        t = g.groupby("category")["population_sum"].sum().reindex(CATS).fillna(0).round(0)
        res["sections"]["population"] = {"status": "available", "unit": "people (WorldPop modelled, 2020)",
                                         "by_category": t.to_dict(), "total": float(t.sum())}
    else:
        res["sections"]["population"] = {"status": "unavailable", "reason": "WorldPop raster not available"}
    return res


def run() -> list[str]:
    p = art_dir() / "layers" / "susceptibility_grid.gpkg"
    if not p.exists():
        raise Blocked("susceptibility grid not generated (index blocked)", ["susceptibility_index"])
    grid = gpd.read_file(p)
    fac_p = data_dir() / "interim" / "osm_facilities.gpkg"
    fac = None
    if fac_p.exists():
        fac = gpd.read_file(fac_p).to_crs(grid.crs)
        j = gpd.sjoin(fac, grid[["cell_id", "category", "score", "ward_id", "geometry"]], how="inner", predicate="within")
        j.drop(columns="index_right").to_crs(4326).to_file(art_dir() / "layers" / "exposure_facilities.geojson", driver="GeoJSON")
    res = summarise(grid, fac)
    write_json_atomic(art_dir() / "layers" / "exposure_summary.json", res)
    return [str(art_dir() / "layers" / "exposure_summary.json")]
