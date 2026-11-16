# Dataset Audit

_Generated 2026-10-14T07:12:36+00:00 by `scripts/gen_audit.py` from `data/registry/datasets.json`. Nothing here is hand-edited; statuses reflect executed checks only._

| ID | Status | Licence | Pune overlap | Last verified |
|---|---|---|---|---|
| `boundaries_pmc_wards_2022` | **ready_for_analysis** | CC BY-SA 2.5 India (dataset); MIT for answerquest/pune-2022-wards mirror | ok | 2026-10-14T06:36:30+00:00 |
| `boundaries_pmc_admin_wards_2017` | **ready_for_analysis** | CC BY-SA 2.5 India | ok | 2026-10-14T06:36:30+00:00 |
| `dem_cop_glo30` | **blocked_in_environment** | Copernicus DEM licence (free, attribution required) | not_attempted | 2026-10-14T06:36:22+00:00 |
| `landcover_worldcover_2021` | **blocked_in_environment** | CC BY 4.0 | not_attempted | 2026-10-14T06:36:23+00:00 |
| `population_worldpop_2020` | **blocked_in_environment** | CC BY 4.0 | not_attempted | 2026-10-14T06:36:25+00:00 |
| `osm_pune` | **blocked_in_environment** | ODbL 1.0 | not_attempted | 2026-10-14T06:36:26+00:00 |
| `rainfall_openmeteo_archive` | **quality_checked** | CC BY 4.0 (data); API free for non-commercial use | not_attempted | 2026-10-14T07:12:31+00:00 |
| `rainfall_openmeteo_forecast` | **quality_checked** | CC BY 4.0 (data); API free for non-commercial use | not_attempted | 2026-10-14T07:12:34+00:00 |
| `rainfall_imd_gauge` | **discovered** | Varies; IMD data policy applies | not_attempted | — |
| `flood_labels_pune` | **unavailable** | n/a | not_attempted | 2026-10-13T07:29:25+00:00 |
| `boundaries_pcmc_wards` | **ready_for_analysis** | CC BY-SA 2.5 India | ok | 2026-10-14T06:36:30+00:00 |


## Pune electoral wards (2022) (`boundaries_pmc_wards_2022`)
- Publisher: DataMeet Pune chapter (traced by SeerMaps from PMC ward PDFs)
- Source: https://raw.githubusercontent.com/datameet/Municipal_Spatial_Data/master/Pune/pune-electoral-wards_2022.geojson
- Attribution: DataMeet Trust / Nikhil VJ / SeerMaps; source PMC final prabhag rachna 2022
- Version/date range: 2022 (git commit recorded at download) / 2022
- Coverage: Pune Municipal Corporation area, 58 wards
- Resolution: vector (hand-traced from PDF maps) spatial, static temporal
- Format/units: GeoJSON / EPSG:4326
- Download method: HTTP GET (raw GitHub)
- **Status: ready_for_analysis**
- Retrieval: `{"state": "ok", "bytes": 256530, "skipped_existing": true}`
- Parse: `{"state": "ok", "crs": "EPSG:4326", "features": 58}`
- Intended use: Study-area definition, zonal aggregation unit, ward-level reporting
- Known limitations:
  - Manually traced from PDF maps - not an official survey-grade boundary
  - Electoral wards, not hydrological or drainage units
  - Post-2022 PMC boundary changes not reflected
- Quality checks:
  - PASS `has_crs` — EPSG:4326
  - PASS `min_feature_count` — 58 features (min 58)
  - PASS `no_empty_geometry` — 0
  - PASS `no_null_geometry` — 0
  - PASS `valid_geometry` — 0 invalid
  - PASS `geometry_types` — ['MultiPolygon']
  - PASS `no_duplicate_geometries` — 0 duplicates
  - PASS `within_pune_window` — [73.7319, 18.3854, 74.0184, 18.6218]
  - PASS `geometries_repaired` — 0

## Pune administrative wards (2017) (`boundaries_pmc_admin_wards_2017`)
- Publisher: DataMeet Pune chapter
- Source: https://raw.githubusercontent.com/datameet/Municipal_Spatial_Data/master/Pune/pune-admin-wards_2017.geojson
- Attribution: DataMeet Trust
- Version/date range: 2017 / 2017
- Coverage: Pune Municipal Corporation, 15 admin wards
- Resolution: vector spatial, static temporal
- Format/units: GeoJSON / EPSG:4326
- Download method: HTTP GET (raw GitHub)
- **Status: ready_for_analysis**
- Retrieval: `{"state": "ok", "bytes": 297307, "skipped_existing": true}`
- Parse: `{"state": "ok", "crs": "EPSG:4326", "features": 15}`
- Intended use: Context overlay (superseded by 2022 wards for analysis)
- Known limitations:
  - 2017 vintage; does not represent current municipal wards
- Quality checks:
  - PASS `has_crs` — EPSG:4326
  - PASS `min_feature_count` — 15 features (min 15)
  - PASS `no_empty_geometry` — 0
  - PASS `no_null_geometry` — 0
  - PASS `valid_geometry` — 0 invalid
  - PASS `geometry_types` — ['Polygon']
  - PASS `no_duplicate_geometries` — 0 duplicates
  - PASS `within_pune_window` — [73.7516, 18.4288, 73.963, 18.6216]
  - PASS `geometries_repaired` — 0

## Copernicus DEM GLO-30 (DSM) (`dem_cop_glo30`)
- Publisher: ESA / Airbus via AWS Open Data
- Source: https://copernicus-dem-30m.s3.amazonaws.com/
- Attribution: Copernicus DEM GLO-30 (c) DLR e.V. 2010-2014 and (c) Airbus Defence and Space GmbH 2014-2018, provided under COPERNICUS by the EU and ESA
- Version/date range: COG 2021_1 / 2010-2015 acquisition
- Coverage: Global, 1x1 degree tiles N18E073 and N18E074 needed for Pune
- Resolution: 30 m (1 arc-second) spatial, static temporal
- Format/units: Cloud-Optimised GeoTIFF / metres above EGM2008 geoid
- Download method: HTTP GET tiles
- **Status: blocked_in_environment**
- Retrieval: `{"state": "not_attempted"}`
- Parse: `{"state": "not_attempted"}`
- Intended use: Elevation, slope, relative topographic position
- Known limitations:
  - Digital SURFACE model: includes buildings and vegetation canopy, not bare earth
  - 30 m is coarse for street-level drainage
- Access probe (2026-10-14T06:36:17+00:00): dns_ok=True, http=200, error=None

## ESA WorldCover 2021 v200 (`landcover_worldcover_2021`)
- Publisher: ESA WorldCover consortium
- Source: https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_N18E072_Map.tif
- Attribution: (c) ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium
- Version/date range: v200 / 2021
- Coverage: Global; 3x3 degree tile N18E072 covers Pune
- Resolution: 10 m spatial, static (annual) temporal
- Format/units: GeoTIFF (COG) / class codes (10 tree, 20 shrub, 30 grass, 40 crop, 50 built-up, 60 bare, 70 snow, 80 water, 90 wetland, 95 mangrove, 100 moss)
- Download method: HTTP GET tile
- **Status: blocked_in_environment**
- Retrieval: `{"state": "not_attempted"}`
- Parse: `{"state": "not_attempted"}`
- Intended use: Built-up and vegetated land-cover shares
- Known limitations:
  - Land-cover class, NOT measured impervious-surface fraction
  - Class accuracy varies in dense urban/peri-urban mix
- Access probe (2026-10-14T06:36:22+00:00): dns_ok=True, http=200, error=None

## WorldPop India 1 km/100 m population 2020 (`population_worldpop_2020`)
- Publisher: WorldPop, University of Southampton
- Source: https://data.worldpop.org/GIS/Population/Global_2000_2020/2020/IND/ind_ppp_2020.tif
- Attribution: WorldPop (www.worldpop.org)
- Version/date range: 2020 (UN-adjusted? to be verified from file metadata) / 2020
- Coverage: India national raster
- Resolution: ~100 m (3 arc-second) spatial, static (annual) temporal
- Format/units: GeoTIFF / people per pixel (to be verified from metadata)
- Download method: HTTP range read / full download
- **Status: blocked_in_environment**
- Retrieval: `{"state": "not_attempted"}`
- Parse: `{"state": "not_attempted"}`
- Intended use: Population exposure per susceptibility zone
- Known limitations:
  - Modelled disaggregation, not a census count
  - Year 2020 - older than current population
- Access probe (2026-10-14T06:36:23+00:00): dns_ok=True, http=200, error=None

## OpenStreetMap infrastructure extract (Pune bbox) (`osm_pune`)
- Publisher: OpenStreetMap contributors via Overpass API
- Source: https://overpass-api.de/api/interpreter
- Attribution: (c) OpenStreetMap contributors
- Version/date range: live query; timestamp recorded / retrieval date
- Coverage: Pune study-area bbox
- Resolution: vector spatial, continuously edited temporal
- Format/units: Overpass JSON -> GeoPackage / n/a
- Download method: HTTP POST Overpass QL
- **Status: blocked_in_environment**
- Retrieval: `{"state": "not_attempted"}`
- Parse: `{"state": "not_attempted"}`
- Intended use: Waterways, roads, hospitals, clinics, schools, fire/police stations
- Known limitations:
  - Completeness varies; counts are NOT a verified inventory
  - Waterway mapping omits many culverted/nallah channels
- Access probe (2026-10-14T06:36:25+00:00): dns_ok=True, http=200, error=None

## Open-Meteo Historical Weather API (reanalysis, hourly precipitation) (`rainfall_openmeteo_archive`)
- Publisher: Open-Meteo.com
- Source: https://archive-api.open-meteo.com/v1/archive
- Attribution: Weather data by Open-Meteo.com
- Version/date range: API v1 / 1940-present
- Coverage: Global grid (~0.25 deg / 9-25 km depending on model)
- Resolution: grid cell spatial, hourly temporal
- Format/units: JSON / mm
- Download method: HTTP GET
- **Status: quality_checked**
- Retrieval: `{"state": "ok", "start": "2019-08-15", "end": "2019-10-15", "lat": 18.539, "lon": 73.857}`
- Parse: `{"state": "ok", "rows": 1488, "missing_rows": 0, "units": "mm", "timezone": "Asia/Kolkata"}`
- Intended use: Rainfall context and rolling accumulations at the study-area centroid
- Known limitations:
  - Gridded reanalysis - NOT a rain-gauge measurement
  - Grid scale smooths convective extremes typical of Pune cloudbursts
- Access probe (2026-10-14T06:36:26+00:00): dns_ok=True, http=200, error=None

## Open-Meteo Forecast API (hourly precipitation) (`rainfall_openmeteo_forecast`)
- Publisher: Open-Meteo.com
- Source: https://api.open-meteo.com/v1/forecast
- Attribution: Weather data by Open-Meteo.com
- Version/date range: API v1 / now to +16 days
- Coverage: Global grid
- Resolution: grid cell spatial, hourly temporal
- Format/units: JSON / mm
- Download method: HTTP GET
- **Status: quality_checked**
- Retrieval: `{"state": "ok"}`
- Parse: `{"state": "ok", "rows": 168, "units": "mm"}`
- Intended use: Forecast rainfall context (kept separate from historical)
- Known limitations:
  - Model forecast; not an official IMD warning
- Access probe (2026-10-14T06:36:28+00:00): dns_ok=True, http=200, error=None

## IMD rainfall observations (gauge/gridded) (`rainfall_imd_gauge`)
- Publisher: India Meteorological Department
- Source: https://mausam.imd.gov.in/
- Attribution: India Meteorological Department
- Version/date range: n/a / n/a
- Coverage: India
- Resolution: gauge / 0.25 deg grid spatial, daily temporal
- Format/units: web portal / request-based / mm
- Download method: No verified programmatic endpoint identified
- **Status: discovered**
- Retrieval: `{"state": "not_attempted"}`
- Parse: `{"state": "not_attempted"}`
- Intended use: Authoritative gauge rainfall (future work)
- Known limitations:
  - Programmatic access not verified; may require registration

## Georeferenced Pune flood observations / inundation footprints (`flood_labels_pune`)
- Publisher: none identified
- Source: n/a
- Attribution: n/a
- Version/date range: n/a / Sept 2019 event of interest
- Coverage: Pune
- Resolution: n/a spatial, event temporal
- Format/units: n/a / n/a
- Download method: see audit
- **Status: unavailable**
- Retrieval: `{"state": "not_attempted"}`
- Parse: `{"state": "not_applicable"}`
- Intended use: Supervised labels (only if credible, georeferenced, downloadable)
- Known limitations:
  - No credible downloadable georeferenced label set has been verified; see docs/dataset_audit.md
- **Blocker:** No georeferenced, downloadable, provenance-documented Pune flood observation or inundation-footprint dataset was found. Candidate evidence is limited to news reports (non-spatial).
- Quality checks:
  - PASS `search_executed` — 1 web search ('Pune flood September 2019 inundation map Sentinel-1 dataset') on 2026-10-13; NOT exhaustive
  - FAIL `candidate_pune_news_report` — Down To Earth via PreventionWeb: 25 Sep 2019 inundation, 87.3 mm rainfall, >=17 deaths. Category 2 (report without precise spatial observations). Not usable as labels.
  - FAIL `candidate_non_pune_sar_studies` — Kerala 2018/2019, Malda 2019, Bangladesh 2019 SAR flood maps surfaced. REJECTED: not Pune.
  - FAIL `sentinel1_derived_water_mask` — Would require Copernicus Data Space/GEE access plus network egress (blocked here). Unconfirmed water masks would also not qualify as verified floodwater without validation.

## Pimpri-Chinchwad electoral wards (vintage undocumented) (`boundaries_pcmc_wards`)
- Publisher: DataMeet Pune chapter (scraped from Shelter Associates spatial slum information)
- Source: https://raw.githubusercontent.com/datameet/Municipal_Spatial_Data/master/PCMC/pcmc-electoral-wards.geojson
- Attribution: DataMeet Trust; source: shelter-associates.org (scraped)
- Version/date range: undocumented / undocumented
- Coverage: Pimpri-Chinchwad Municipal Corporation, 66 wards
- Resolution: vector spatial, static temporal
- Format/units: GeoJSON / EPSG:4979 (3D geographic; treated as WGS84)
- Download method: HTTP GET (raw GitHub)
- **Status: ready_for_analysis**
- Retrieval: `{"state": "ok", "bytes": 168077, "skipped_existing": true}`
- Parse: `{"state": "ok", "crs": "EPSG:4979", "features": 66}`
- Intended use: Extends the study area to the wider Pune urban area (PMC + PCMC)
- Known limitations:
  - Scraped from a third party; ward vintage not documented (likely older than the 2022 PMC file)
  - Electoral wards, not drainage units
  - Boundaries may not align exactly with PMC 2022 wards (possible gaps/overlaps)
- Quality checks:
  - PASS `has_crs` — EPSG:4326
  - PASS `min_feature_count` — 66 features (min 66)
  - PASS `no_empty_geometry` — 0
  - PASS `no_null_geometry` — 0
  - PASS `valid_geometry` — 0 invalid
  - PASS `geometry_types` — ['Polygon']
  - PASS `no_duplicate_geometries` — 0 duplicates
  - PASS `within_pune_window` — [73.7104, 18.5639, 73.934, 18.7211]
  - PASS `geometries_repaired` — 0

## Flood-label research note
One web search was executed (not exhaustive). Pune's 25 Sept 2019 flood is documented in news reporting (Down To Earth via PreventionWeb) but no georeferenced, downloadable, provenance-documented observation set was found. SAR flood-mapping studies surfaced were for Kerala, Malda and Bangladesh and were rejected as non-Pune. The Chennai-specific material mentioned in the brief was not used.
