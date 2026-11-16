# API (OpenAPI at `/docs`)
Always available: `/api/health /status /metadata /study-area /boundaries/wards /datasets /datasets/{id} /features/manifest /susceptibility/config /model/metrics /pipeline/status /pipeline/probe`.
Data-dependent (HTTP 503 `{detail:{status:"unavailable",module,reason,upstream_stages}}` until produced): `/rainfall /rainfall/series?kind=&agg=&start=&end= /terrain/summary /landcover/summary /susceptibility/metadata|zones|grid?bbox=&category=&limit=&offset= /exposure/summary /exposure/facilities?type=&bbox= /model/explainability`.
`POST /scenarios/evaluate` body: `{name, rainfall_multiplier 0.5–3 (not applied), window_hours∈{1,3,6,12,24,72}, weights{var:0–1}, top_n}` → comparison, assumptions, `not_applied`, `not_a_forecast:true`, deterministic `scenario_id`.
Validation: 422 for bad bbox (order, outside Pune region), bad enums, out-of-range weights. 429 when rate limit exceeded.
