# Deployment
Local: see README. Container: `docker compose up app` serves API+UI on :8000 with volumes `/data`, `/artifacts`; populate by `docker compose --profile pipeline run --rm pipeline` (needs egress to the hosts in the registry). Env: `FLOODX_DATA_DIR, FLOODX_ARTIFACTS_DIR, FLOODX_CORS_ORIGINS, FLOODX_RATE_LIMIT_PER_MIN, FLOODX_CONTACT`; frontend `VITE_API_URL` if hosted separately. No secrets required.
**Status: not deployed anywhere; Docker image not built (no Docker in the dev sandbox).**
