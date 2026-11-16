"""E2E: synthetic site -> pipeline -> real uvicorn process -> HTTP, incl. the built frontend bundle.
Data is SYNTHETIC and lives in a tmp dir. Requires frontend/dist (run `npm run build`)."""
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

from pipeline.exposure import analysis as exposure
from pipeline.features import build
from pipeline.inference import susceptibility
from pipeline.preprocessing import grid, study_area

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def live(synth_site):
    d, a = synth_site
    study_area.run(); grid.run(); build.terrain_stage(); build.run(); susceptibility.run(); exposure.run()
    port = 8765
    env = {**os.environ, "FLOODX_DATA_DIR": str(d), "FLOODX_ARTIFACTS_DIR": str(a)}
    p = subprocess.Popen([sys.executable, "-m", "uvicorn", "backend.app.main:app", "--port", str(port), "--log-level", "warning"], cwd=ROOT, env=env)
    base = f"http://127.0.0.1:{port}"
    for _ in range(60):
        try:
            if httpx.get(f"{base}/api/health", timeout=1).status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.5)
    else:
        p.kill(); pytest.fail("server did not start")
    yield base
    p.terminate(); p.wait(10)


def test_full_journey(live):
    s = httpx.get(f"{live}/api/status").json()
    assert s["susceptibility_available"] is True and s["active_path"] in ("A", "B", None)
    grid_ = httpx.get(f"{live}/api/susceptibility/grid?limit=5000").json()
    n = len(grid_["features"]); assert n > 10
    zones = httpx.get(f"{live}/api/susceptibility/zones").json()
    assert len(zones["features"]) == 4
    scen = httpx.post(f"{live}/api/scenarios/evaluate", json={"weights": {"builtup_share": 0.9}})
    assert scen.status_code == 200 and scen.json()["not_a_forecast"]
    assert httpx.get(f"{live}/api/exposure/summary").json()["sections"]["facilities"]["status"] == "available"
    assert httpx.get(f"{live}/docs").status_code == 200
    dist = ROOT / "frontend" / "dist" / "index.html"
    if dist.exists():
        r = httpx.get(f"{live}/")
        assert r.status_code == 200 and "FLOOD-X" in r.text
