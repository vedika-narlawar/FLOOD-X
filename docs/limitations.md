# Limitations
1. Real DEM, land cover, population, OSM and rainfall have not been retrieved/validated here (network blocked); the susceptibility layer, exposure figures and rainfall views are therefore empty until the pipeline is run with internet.
2. Index weights are uncalibrated priors; no validation against observed floods; quintile categories are relative.
3. 30 m DSM includes buildings/canopy; 500 m grid; no flow accumulation; OSM omits many culverted nallahs and its counts are not a verified inventory; built-up class ≠ imperviousness; WorldPop is modelled 2020.
4. Wards are hand-traced 2022 electoral boundaries (not drainage units; later changes not reflected). The 2017 admin file has 15 polygons (verified) and is context only.
5. Flood-label search was a single web query — not exhaustive; IMD data and Sentinel-1 water masks were not pursued.
6. Rate limiter is in-memory/per-process; no auth; no PostGIS; Docker/deploy untested; frontend tested with jsdom (map mocked), no browser screenshots.
