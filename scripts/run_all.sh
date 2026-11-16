#!/usr/bin/env bash
# One-command local run. Requires internet for the real data stages.
set -euo pipefail
cd "$(dirname "$0")/.."
pip install -r requirements.txt
python -m pipeline.run                 # idempotent; blocked stages are recorded, not faked
python scripts/gen_audit.py
(cd frontend && npm ci && npm run build)
exec uvicorn backend.app.main:app --port 8000   # serves API + built frontend at http://localhost:8000
