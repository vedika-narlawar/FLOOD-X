# Architecture
```
Remote sources ─► pipeline/ingestion ─► data/raw (immutable, sha256) ─► validation ─► data/interim
   ─► preprocessing (study area, 500 m UTM grid) ─► features (terrain, land cover, population, OSM) ─► data/processed/features (GeoParquet + manifest)
   ─► modeling/index (screening index) + sensitivity ─► inference (layers) ─► exposure ─► artifacts/layers, artifacts/metrics
FastAPI (backend/app) ◄── reads artifacts only ──► React UI
```
- State ledgers: `data/registry/datasets.json` (dataset provenance/status), `artifacts/pipeline_status.json` (stage outcomes + history).
- Failure semantics: `Blocked` (missing inputs) / `SourceUnavailable` (network) → stage `blocked`; unexpected errors → `failed`; both recorded, neither fabricated.
- Stale outputs are deleted when the index becomes non-computable so the API never serves an old run as current.
- Analysis CRS: UTM selected from study-area centroid (EPSG:32643); delivery CRS EPSG:4326.
- Safeguards: atomic downloads (`.part` → rename), gzip-aware truncation check, bounded retries, DNS fail-fast, rate limiting (in-memory), CORS allow-list, bbox/limit validation.
