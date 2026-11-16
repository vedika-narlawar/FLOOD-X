import json

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from pipeline import registry
from pipeline.exposure import analysis as exposure
from pipeline.features import build
from pipeline.inference import susceptibility
from pipeline.preprocessing import grid, study_area

c = TestClient(app)


def test_health_and_unavailable_semantics(dirs):
    assert c.get("/api/health").json()["status"] == "ok"
    r = c.get("/api/susceptibility/zones")
    assert r.status_code == 503
    det = r.json()["detail"]
    assert det["status"] == "unavailable" and det["reason"] and "upstream_stages" in det
    for u in ("/api/rainfall", "/api/rainfall/series", "/api/terrain/summary", "/api/landcover/summary", "/api/exposure/summary",
              "/api/exposure/facilities", "/api/susceptibility/grid", "/api/susceptibility/metadata", "/api/model/explainability"):
        assert c.get(u).status_code == 503, u


def test_datasets_routes(dirs):
    registry.load()
    ds = c.get("/api/datasets").json()
    assert {d["id"] for d in ds} >= {"dem_cop_glo30", "flood_labels_pune"}
    assert c.get("/api/datasets/dem_cop_glo30").json()["licence"]
    assert c.get("/api/datasets/zzz").status_code == 404


def test_model_metrics_is_honest_without_labels(dirs):
    from pipeline.modeling.label_audit import audit
    audit()
    m = c.get("/api/model/metrics").json()
    assert m["status"] == "not_applicable" and m["metrics"] is None and m["supervised_model_trained"] is False


def test_validation_errors(dirs):
    assert c.post("/api/scenarios/evaluate", json={"rainfall_multiplier": 10}).status_code == 422
    assert c.post("/api/scenarios/evaluate", json={"window_hours": 5}).status_code == 422
    assert c.post("/api/scenarios/evaluate", json={"weights": {"builtup_share": 2}}).status_code == 422
    assert c.get("/api/rainfall/series?kind=weird").status_code == 422


@pytest.fixture
def full(synth_site):
    study_area.run(); grid.run(); build.terrain_stage(); build.run(); susceptibility.run(); exposure.run()
    return synth_site


def test_served_layers_and_bbox_filtering(full):
    g = c.get("/api/susceptibility/grid?limit=10").json()
    assert len(g["features"]) == 10 and g["metadata"]["total_matching"] > 10
    west = c.get("/api/susceptibility/grid?bbox=73.79,18.49,73.82,18.55&limit=5000").json()
    east = c.get("/api/susceptibility/grid?bbox=73.82,18.49,73.85,18.55&limit=5000").json()
    assert 0 < len(west["features"]) < g["metadata"]["total_matching"] and len(east["features"]) > 0
    assert c.get("/api/susceptibility/grid?bbox=73.9,18.5,73.8,18.6").status_code == 422
    assert c.get("/api/susceptibility/grid?bbox=10,10,11,11").status_code == 422
    assert c.get("/api/susceptibility/grid?bbox=abc").status_code == 422
    z = c.get("/api/susceptibility/zones").json()
    assert len(z["features"]) == 4
    cat = c.get("/api/susceptibility/grid?category=Very%20high&limit=5000").json()
    assert all(f["properties"]["category"] == "Very high" for f in cat["features"])
    assert c.get("/api/exposure/facilities?type=school").json()["features"].__len__() == 2
    assert c.get("/api/exposure/facilities?type=casino").status_code == 422
    assert c.get("/api/terrain/summary").json()["elev_mean_m"]["units"].startswith("m")
    assert "builtup_share" in c.get("/api/landcover/summary").json()
    ex = c.get("/api/model/explainability").json()
    gj = c.get("/api/susceptibility/grid?limit=5000").json()
    mean_score = sum(f["properties"]["score"] for f in gj["features"]) / len(gj["features"])
    assert sum(ex["mean_score_contribution"].values()) == pytest.approx(mean_score, rel=1e-6)  # additive decomposition is exact


def test_scenario_weights_applied_rainfall_not_applied(full):
    base = c.post("/api/scenarios/evaluate", json={}).json()
    assert base["comparison"]["spearman_rank_correlation"] == pytest.approx(1.0) and base["comparison"]["cells_changing_category"] == 0
    s = c.post("/api/scenarios/evaluate", json={"weights": {"builtup_share": 1.0, "elev_mean_m": 0.0}, "rainfall_multiplier": 2.0}).json()
    assert s["not_a_forecast"] is True and s["not_applied"][0]["parameter"].startswith("rainfall")
    assert s["comparison"]["spearman_rank_correlation"] < 1.0
    assert s["applied"]["weights"]["builtup_share"] == 1.0
    # rainfall multiplier alone must not change anything (it is not modelled)
    r2 = c.post("/api/scenarios/evaluate", json={"rainfall_multiplier": 3.0}).json()
    assert r2["comparison"]["cells_changing_category"] == 0
    # reproducible id
    assert c.post("/api/scenarios/evaluate", json={"rainfall_multiplier": 3.0}).json()["scenario_id"] == r2["scenario_id"]
    assert c.post("/api/scenarios/evaluate", json={"weights": {"bogus": 0.5}}).status_code == 503


def test_rainfall_routes_with_synthetic_series(dirs):
    d, _ = dirs
    registry.load(); registry.update("rainfall_openmeteo_archive", retrieved_at="t", retrieval={"state": "ok"})
    t = pd.date_range("2019-09-24", periods=72, freq="h")
    df = pd.DataFrame({"time": t, "precipitation_mm": 1.0, "missing": False})
    df.loc[5, ["precipitation_mm", "missing"]] = [None, True]
    from pipeline.ingestion.rainfall import rolling_accumulations
    pd.concat([df, rolling_accumulations(df).drop(columns="time")], axis=1).to_parquet(d / "processed" / "rainfall_historical.parquet")
    r = c.get("/api/rainfall").json()
    assert r["units"] == "mm" and r["missing_hours"] == 1 and "not a rain-gauge" in r["caveat"].lower()
    s = c.get("/api/rainfall/series?agg=daily").json()
    assert s["n"] == 3 and s["data"][0]["missing"] == 1
    assert c.get("/api/rainfall/series?kind=forecast").status_code == 503


def test_rate_limit(dirs, monkeypatch):
    monkeypatch.setenv("FLOODX_RATE_LIMIT_PER_MIN", "3")
    from backend.app import main
    main._hits.clear()
    codes = [c.get("/api/health").status_code for _ in range(5)]
    assert 429 in codes
    main._hits.clear()
