from __future__ import annotations

import geopandas as gpd

from .. import registry
from ..common import Blocked, data_dir, get_logger
from ..geo import study_utm

log = get_logger("floodx.study_area")


def build_study_area(wards: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    wards = wards.to_crs(4326)
    geom = wards.geometry.union_all().buffer(0)
    epsg = study_utm(wards)
    g = gpd.GeoDataFrame({"name": ["Pune Municipal Corporation study area (union of 2022 electoral wards)"],
                          "utm_epsg": [epsg]}, geometry=[geom], crs=4326)
    g["area_km2"] = g.to_crs(epsg).area / 1e6
    g["n_wards"] = len(wards)
    return g


def run() -> list[str]:
    src = data_dir() / "interim" / "boundaries_pmc_wards_2022.gpkg"
    if not src.exists():
        raise Blocked("2022 ward boundaries not ingested", ["boundaries"])
    wards = gpd.read_file(src).to_crs(4326)
    pcmc = data_dir() / "interim" / "boundaries_pcmc_wards.gpkg"
    if pcmc.exists():  # optional: extend to PMC + Pimpri-Chinchwad
        wards = gpd.GeoDataFrame(geometry=list(wards.geometry) + list(gpd.read_file(pcmc).to_crs(4326).geometry), crs=4326)
    sa = build_study_area(wards)
    sa["name"] = "Pune urban area study area (union of PMC 2022 + PCMC electoral wards)" if pcmc.exists() else sa["name"]
    out = data_dir() / "interim" / "study_area.gpkg"
    sa.to_file(out, driver="GPKG")
    log.info("study area: %.1f km2, EPSG:%s", sa.area_km2.iloc[0], sa.utm_epsg.iloc[0])
    return [str(out)]
