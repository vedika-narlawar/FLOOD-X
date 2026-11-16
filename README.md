# FLOOD-X — Urban Flood Susceptibility Screening & Exposure Platform for Pune

**Analytical method: explainable GIS-based Flood Susceptibility Screening Index. No supervised model is trained.**
Reason: no credible, georeferenced, downloadable Pune flood-observation dataset was found (see `docs/dataset_audit.md`); training would require inventing labels.

Outputs are **relative screening scores**, not flood probabilities, hazard, depth, extent, predictions or warnings.

## Implemented vs pending (honest status as of last run)

| Capability | State |
|---|---|
| Dataset registry, provenance, access probes, label audit | **Implemented & executed** |
| Pune 2022 PMC wards (58), PCMC wards (66, vintage undocumented), 2017 admin wards (15, context): download, hash, validation | **Executed on real data** |
| Study area = PMC + Pimpri-Chinchwad (683.4 km², EPSG:32643, 124 wards) and 500 m analysis grid (2,924 cells) | **Executed on real data** |
| Map: ward outlines, ward susceptibility choropleth, high-susceptibility highlighting, reset-to-all-Pune | **Implemented; risk highlighting stays empty until real scores exist** |
| DEM / WorldCover / WorldPop / OSM / Open-Meteo ingestion clients, validators, terrain + feature + index + exposure + scenario code | **Implemented, unit/integration-tested on synthetic fixtures; NOT yet executed on real provider data** (sandbox could not resolve those hosts) |
| Real susceptibility layer, exposure numbers, rainfall charts | **Pending** — appear automatically once `python -m pipeline.run` succeeds on a networked machine |
| Flow accumulation | Not implemented (needs hydrologically conditioned DEM) |
| Supervised model, calibrated probabilities, flood depth/extent | Not implemented / not claimed |
| Raster tile serving (elevation/land-cover/population layers in map) | Not implemented; grid choropleths of derived features are served instead |
| PostGIS | Not used (GeoPackage/GeoParquet/GeoJSON files); no Postgres in sandbox |
| Public deployment | **Not deployed.** Docker files written but not built/run (no Docker in sandbox) |

## Quick start (needs internet for real data)
```bash
pip install -r requirements.txt
python -m pipeline.run            # restartable; writes artifacts/pipeline_status.json
python scripts/gen_audit.py       # regenerates docs/dataset_audit.md & data_quality_report.md
cd frontend && npm ci && npm run build && cd ..
uvicorn backend.app.main:app --port 8000      # http://localhost:8000 (API + UI), docs at /docs
# dev UI: (cd frontend && npm run dev)  -> http://localhost:5173 (proxies /api to :8000)
```
Single stage: `python -m pipeline.run --stage download_dem --force`. Docker: `docker compose up app`; `docker compose --profile pipeline run --rm pipeline`.

## Tests
`python -m pytest tests -q` (55 tests: unit, synthetic-site integration, API, live-server E2E) · `cd frontend && npm test` (9 tests) · `npm run build` (type-check + bundle).
Synthetic fixtures exist only under `tests/` and never write to `data/` or `artifacts/`.

## Architecture
`pipeline/` (ingestion → validation → preprocessing → features → modeling → inference → exposure; orchestrated by `pipeline/run.py`) writes to `data/` and `artifacts/`; `backend/` (FastAPI) serves only those artifacts and returns structured **503 "unavailable" with upstream stage reasons** when absent; `frontend/` (React/TS/Vite/Tailwind/Leaflet/Recharts/TanStack Query) renders backend responses only. See `docs/architecture.md`.

## Attribution
Ward boundaries © DataMeet Trust (CC BY-SA 2.5 IN) · OSM © OpenStreetMap contributors (ODbL) · Open-Meteo.com (CC BY 4.0) · Copernicus DEM, ESA WorldCover (CC BY 4.0), WorldPop (CC BY 4.0) · Basemap tiles © OpenStreetMap contributors (tile.openstreetmap.org; light/demo use per OSM tile policy).

## Troubleshooting
- Stage `blocked(network)`: host unreachable → run from an open network (check `/api/pipeline/probe`).
- UI shows amber "Unavailable" panels: expected until the stage named in the panel succeeds.
- `rasterio`/`geopandas` install problems: use the Dockerfile (GDAL included).
