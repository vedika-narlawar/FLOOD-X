@echo off
cd /d %~dp0..
pip install -r requirements.txt
python -m pipeline.run
python scripts\gen_audit.py
cd frontend && npm ci && npm run build && cd ..
uvicorn backend.app.main:app --port 8000
