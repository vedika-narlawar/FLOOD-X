"""Machine-readable dataset registry. Seeded with *discovered* sources; statuses are only
advanced by code that has actually performed the corresponding verification."""
from __future__ import annotations

from pathlib import Path

from .common import data_dir, now_iso, read_json, write_json_atomic

STATUSES = ["discovered", "access_verified", "downloaded", "parsed", "spatially_validated",
            "quality_checked", "ready_for_analysis", "unavailable", "rejected", "blocked_in_environment"]

PUNE_BBOX = (73.55, 18.30, 74.15, 18.75)  # generous sanity window (lon_min, lat_min, lon_max, lat_max)


def _ds(id, name, publisher, url, licence, attribution, version, date_range, coverage, res_sp, res_t,
        fmt, units, method, intended, limits):
    return dict(id=id, name=name, publisher=publisher, source_url=url, licence=licence,
                attribution=attribution, version=version, date_range=date_range, geographic_coverage=coverage,
                spatial_resolution=res_sp, temporal_resolution=res_t, format=fmt, units=units,
                download_method=method, status="discovered", retrieval={"state": "not_attempted"},
                parse={"state": "not_attempted"}, pune_overlap={"state": "not_attempted"},
                quality_checks=[], intended_use=intended, known_limitations=limits, blocker=None,
                local_path=None, sha256=None, retrieved_at=None, last_verified=None,
                processing_history=[], licence_source="documented by publisher; not machine-verified")


SEED = [
    _ds("boundaries_pmc_wards_2022", "Pune electoral wards (2022)", "DataMeet Pune chapter (traced by SeerMaps from PMC ward PDFs)",
        "https://raw.githubusercontent.com/datameet/Municipal_Spatial_Data/master/Pune/pune-electoral-wards_2022.geojson",
        "CC BY-SA 2.5 India (dataset); MIT for answerquest/pune-2022-wards mirror",
        "DataMeet Trust / Nikhil VJ / SeerMaps; source PMC final prabhag rachna 2022",
        "2022 (git commit recorded at download)", "2022", "Pune Municipal Corporation area, 58 wards",
        "vector (hand-traced from PDF maps)", "static", "GeoJSON", "EPSG:4326", "HTTP GET (raw GitHub)",
        "Study-area definition, zonal aggregation unit, ward-level reporting",
        ["Manually traced from PDF maps - not an official survey-grade boundary",
         "Electoral wards, not hydrological or drainage units", "Post-2022 PMC boundary changes not reflected"]),
    _ds("boundaries_pmc_admin_wards_2017", "Pune administrative wards (2017)", "DataMeet Pune chapter",
        "https://raw.githubusercontent.com/datameet/Municipal_Spatial_Data/master/Pune/pune-admin-wards_2017.geojson",
        "CC BY-SA 2.5 India", "DataMeet Trust", "2017", "2017", "Pune Municipal Corporation, 15 admin wards",
        "vector", "static", "GeoJSON", "EPSG:4326", "HTTP GET (raw GitHub)", "Context overlay (superseded by 2022 wards for analysis)",
        ["2017 vintage; does not represent current municipal wards"]),
    _ds("boundaries_pcmc_wards", "Pimpri-Chinchwad electoral wards (vintage undocumented)", "DataMeet Pune chapter (scraped from Shelter Associates spatial slum information)",
        "https://raw.githubusercontent.com/datameet/Municipal_Spatial_Data/master/PCMC/pcmc-electoral-wards.geojson",
        "CC BY-SA 2.5 India", "DataMeet Trust; source: shelter-associates.org (scraped)", "undocumented", "undocumented",
        "Pimpri-Chinchwad Municipal Corporation, 66 wards", "vector", "static", "GeoJSON", "EPSG:4979 (3D geographic; treated as WGS84)",
        "HTTP GET (raw GitHub)", "Extends the study area to the wider Pune urban area (PMC + PCMC)",
        ["Scraped from a third party; ward vintage not documented (likely older than the 2022 PMC file)",
         "Electoral wards, not drainage units", "Boundaries may not align exactly with PMC 2022 wards (possible gaps/overlaps)"]),
    _ds("dem_cop_glo30", "Copernicus DEM GLO-30 (DSM)", "ESA / Airbus via AWS Open Data",
        "https://copernicus-dem-30m.s3.amazonaws.com/",
        "Copernicus DEM licence (free, attribution required)", "Copernicus DEM GLO-30 (c) DLR e.V. 2010-2014 and (c) Airbus Defence and Space GmbH 2014-2018, provided under COPERNICUS by the EU and ESA",
        "COG 2021_1", "2010-2015 acquisition", "Global, 1x1 degree tiles N18E073 and N18E074 needed for Pune",
        "30 m (1 arc-second)", "static", "Cloud-Optimised GeoTIFF", "metres above EGM2008 geoid", "HTTP GET tiles",
        "Elevation, slope, relative topographic position",
        ["Digital SURFACE model: includes buildings and vegetation canopy, not bare earth", "30 m is coarse for street-level drainage"]),
    _ds("landcover_worldcover_2021", "ESA WorldCover 2021 v200", "ESA WorldCover consortium",
        "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_N18E072_Map.tif",
        "CC BY 4.0", "(c) ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium",
        "v200", "2021", "Global; 3x3 degree tile N18E072 covers Pune", "10 m", "static (annual)", "GeoTIFF (COG)",
        "class codes (10 tree, 20 shrub, 30 grass, 40 crop, 50 built-up, 60 bare, 70 snow, 80 water, 90 wetland, 95 mangrove, 100 moss)",
        "HTTP GET tile", "Built-up and vegetated land-cover shares",
        ["Land-cover class, NOT measured impervious-surface fraction", "Class accuracy varies in dense urban/peri-urban mix"]),
    _ds("population_worldpop_2020", "WorldPop India 1 km/100 m population 2020", "WorldPop, University of Southampton",
        "https://data.worldpop.org/GIS/Population/Global_2000_2020/2020/IND/ind_ppp_2020.tif",
        "CC BY 4.0", "WorldPop (www.worldpop.org)", "2020 (UN-adjusted? to be verified from file metadata)", "2020", "India national raster",
        "~100 m (3 arc-second)", "static (annual)", "GeoTIFF", "people per pixel (to be verified from metadata)", "HTTP range read / full download",
        "Population exposure per susceptibility zone", ["Modelled disaggregation, not a census count", "Year 2020 - older than current population"]),
    _ds("osm_pune", "OpenStreetMap infrastructure extract (Pune bbox)", "OpenStreetMap contributors via Overpass API",
        "https://overpass-api.de/api/interpreter", "ODbL 1.0", "(c) OpenStreetMap contributors", "live query; timestamp recorded",
        "retrieval date", "Pune study-area bbox", "vector", "continuously edited", "Overpass JSON -> GeoPackage", "n/a",
        "HTTP POST Overpass QL", "Waterways, roads, hospitals, clinics, schools, fire/police stations",
        ["Completeness varies; counts are NOT a verified inventory", "Waterway mapping omits many culverted/nallah channels"]),
    _ds("rainfall_openmeteo_archive", "Open-Meteo Historical Weather API (reanalysis, hourly precipitation)", "Open-Meteo.com",
        "https://archive-api.open-meteo.com/v1/archive", "CC BY 4.0 (data); API free for non-commercial use",
        "Weather data by Open-Meteo.com", "API v1", "1940-present", "Global grid (~0.25 deg / 9-25 km depending on model)",
        "grid cell", "hourly", "JSON", "mm", "HTTP GET", "Rainfall context and rolling accumulations at the study-area centroid",
        ["Gridded reanalysis - NOT a rain-gauge measurement", "Grid scale smooths convective extremes typical of Pune cloudbursts"]),
    _ds("rainfall_openmeteo_forecast", "Open-Meteo Forecast API (hourly precipitation)", "Open-Meteo.com",
        "https://api.open-meteo.com/v1/forecast", "CC BY 4.0 (data); API free for non-commercial use", "Weather data by Open-Meteo.com",
        "API v1", "now to +16 days", "Global grid", "grid cell", "hourly", "JSON", "mm", "HTTP GET",
        "Forecast rainfall context (kept separate from historical)", ["Model forecast; not an official IMD warning"]),
    _ds("rainfall_imd_gauge", "IMD rainfall observations (gauge/gridded)", "India Meteorological Department",
        "https://mausam.imd.gov.in/", "Varies; IMD data policy applies", "India Meteorological Department", "n/a", "n/a",
        "India", "gauge / 0.25 deg grid", "daily", "web portal / request-based", "mm",
        "No verified programmatic endpoint identified", "Authoritative gauge rainfall (future work)",
        ["Programmatic access not verified; may require registration"]),
    _ds("flood_labels_pune", "Georeferenced Pune flood observations / inundation footprints", "none identified",
        "n/a", "n/a", "n/a", "n/a", "Sept 2019 event of interest", "Pune", "n/a", "event", "n/a", "n/a", "see audit",
        "Supervised labels (only if credible, georeferenced, downloadable)",
        ["No credible downloadable georeferenced label set has been verified; see docs/dataset_audit.md"]),
]


def path() -> Path:
    return data_dir() / "registry" / "datasets.json"


def load() -> dict:
    reg = read_json(path())
    if reg is None:
        reg = {"schema_version": 1, "created_at": now_iso(), "datasets": {d["id"]: d for d in SEED}}
        write_json_atomic(path(), reg)
    # add newly seeded datasets without clobbering verified state
    for d in SEED:
        reg["datasets"].setdefault(d["id"], d)
    return reg


def update(ds_id: str, *, status: str | None = None, history: str | None = None, **fields) -> dict:
    reg = load()
    d = reg["datasets"][ds_id]
    if status:
        assert status in STATUSES, status
        d["status"] = status
    d.update(fields)
    if history:
        d["processing_history"].append({"at": now_iso(), "step": history})
    d["last_verified"] = now_iso()
    write_json_atomic(path(), reg)
    return d
