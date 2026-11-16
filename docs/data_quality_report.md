# Data Quality Report

_Generated 2026-10-14T07:12:36+00:00._

## Pipeline stage outcomes

| Stage | Status | Message |
|---|---|---|
| `registry_init` | success | completed |
| `access_probe` | success | completed |
| `boundaries` | success | completed |
| `study_area` | success | completed |
| `grid` | success | completed |
| `label_audit` | success | completed |
| `download_dem` | failed | PermissionError: [WinError 32] The process cannot access the file because it is being used by another process: 'C:\\Users\\nidhi\\Downloads\\flood-x (1)\\flood-x\\data\\raw\\dem\\Copernicus_DSM_COG_10 |
| `download_landcover` | blocked | Remote source unavailable: download failed for https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_N18E072_Map.tif: HTTPSConnectionPool(host='esa-worldcover |
| `download_population` | blocked | Remote source unavailable: WorldPop read failed: Range downloading not supported by this server! |
| `download_osm` | blocked | Remote source unavailable: POST https://overpass-api.de/api/interpreter failed after 3 attempts: HTTPSConnectionPool(host='overpass-api.de', port=443): Read timed out. |
| `download_rainfall` | success | completed |
| `terrain` | failed | RasterioIOError: Read failed. See previous exception for details. |
| `grid_features` | success | completed |
| `susceptibility_index` | blocked | Susceptibility index not computable: only 1 of required minimum 3 variables available. Skipped: ['rel_elev_mean_m (column not present (feature unavailable))', 'elev_mean_m (column not present (feature |
| `exposure` | blocked | susceptibility grid not generated (index blocked) |

## Executed validation (boundaries)

**boundaries_pmc_wards_2022** — sha256 `0142d5477e5a18a7…`, bounds [73.73193, 18.38539, 74.01838, 18.62185]
- PASS has_crs: EPSG:4326
- PASS min_feature_count: 58 features (min 58)
- PASS no_empty_geometry: 0
- PASS no_null_geometry: 0
- PASS valid_geometry: 0 invalid
- PASS geometry_types: ['MultiPolygon']
- PASS no_duplicate_geometries: 0 duplicates
- PASS within_pune_window: [73.7319, 18.3854, 74.0184, 18.6218]
- PASS geometries_repaired: 0
**boundaries_pmc_admin_wards_2017** — sha256 `8988021aa25b9c26…`, bounds [73.75156, 18.42883, 73.96296, 18.62162]
- PASS has_crs: EPSG:4326
- PASS min_feature_count: 15 features (min 15)
- PASS no_empty_geometry: 0
- PASS no_null_geometry: 0
- PASS valid_geometry: 0 invalid
- PASS geometry_types: ['Polygon']
- PASS no_duplicate_geometries: 0 duplicates
- PASS within_pune_window: [73.7516, 18.4288, 73.963, 18.6216]
- PASS geometries_repaired: 0

All raster/OSM/rainfall validators are implemented and unit-tested on synthetic fixtures, but have **not** been run on real provider data in this environment (network blocked).
