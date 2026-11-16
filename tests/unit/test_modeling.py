import json

import numpy as np
import pandas as pd
import pytest

from pipeline.modeling.index import compute_index, load_config, normalise, validate_config, with_weights
from pipeline.modeling.label_audit import audit
from pipeline.modeling.sensitivity import run_sensitivity


def frame(n=300, seed=0):
    r = np.random.default_rng(seed)
    return pd.DataFrame({"rel_elev_mean_m": r.normal(0, 5, n), "elev_mean_m": r.normal(600, 30, n), "slope_mean_deg": r.gamma(2, 2, n),
                         "dist_waterway_m": r.gamma(2, 400, n), "builtup_share": r.uniform(0, 1, n)})


CFG = load_config()


def test_config_valid_and_weights_documented():
    assert abs(sum(v["weight"] for v in CFG["variables"]) - 1.0) < 1e-9
    assert all(v.get("rationale") for v in CFG["variables"]) and CFG["excluded_variables"]


@pytest.mark.parametrize("var,direction", [(v["name"], v["direction"]) for v in CFG["variables"]])
def test_monotonicity(var, direction):
    df = frame()
    base = pd.DataFrame({k: [df[k].median()] * 3 for k in df.columns})
    lo, hi = df[var].quantile(0.1), df[var].quantile(0.9)
    probe = pd.concat([df, base.assign(**{var: [lo, df[var].median(), hi]})], ignore_index=True)
    s, _ = compute_index(probe, CFG)
    s3 = s["score"].iloc[-3:].values
    assert (s3[2] > s3[0]) if direction == "increase" else (s3[2] < s3[0])


def test_reproducible_and_bounded():
    a, _ = compute_index(frame(), CFG); b, _ = compute_index(frame(), CFG)
    pd.testing.assert_frame_equal(a, b)
    assert a["score"].between(0, 100).all()


def test_missing_input_renormalises_not_zero_fills():
    df = frame()
    df.loc[0, "slope_mean_deg"] = np.nan
    s, info = compute_index(df, CFG)
    assert s.loc[0, "n_inputs_used"] == 4 and np.isfinite(s.loc[0, "score"])
    # contribution of the missing variable is exactly absent (NaN), and others re-weighted to sum to the score
    contribs = [c for c in s.columns if c.startswith("contrib_")]
    assert np.isnan(s.loc[0, "contrib_slope_mean_deg"])
    assert s.loc[0, contribs].sum() == pytest.approx(s.loc[0, "score"])


def test_min_inputs_gives_nan_not_imputation():
    df = frame()
    df.loc[1, ["slope_mean_deg", "dist_waterway_m", "builtup_share"]] = np.nan  # only 2 left (<3)
    s, _ = compute_index(df, CFG)
    assert np.isnan(s.loc[1, "score"]) and s.loc[1, "n_inputs_used"] == 2


def test_unavailable_feature_columns_reported_and_blocked_below_minimum():
    s, info = compute_index(frame()[["elev_mean_m", "slope_mean_deg"]], CFG)
    assert not info["computable"] and s["score"].isna().all() and len(info["variables_skipped"]) == 3


def test_constant_variable_is_skipped_not_silently_scored():
    df = frame(); df["builtup_share"] = 0.3
    _, info = compute_index(df, CFG)
    assert "builtup_share" not in info["variables_used"]
    assert any(s["name"] == "builtup_share" and "degenerate" in s["reason"] for s in info["variables_skipped"])


def test_categories_are_quantile_quintiles():
    s, info = compute_index(frame(1000), CFG)
    counts = s["category"].value_counts()
    assert set(counts.index) == set(CFG["categories"]["labels"]) and counts.max() - counts.min() <= 2


def test_weight_changes_change_scores_and_validation():
    df = frame()
    a, _ = compute_index(df, CFG)
    b, _ = compute_index(df, with_weights(CFG, {"builtup_share": 0.9}))
    assert not np.allclose(a["score"], b["score"])
    with pytest.raises(ValueError):
        with_weights(CFG, {"nonsense": 1})
    with pytest.raises(ValueError):
        with_weights(CFG, {v["name"]: 0 for v in CFG["variables"]})
    bad = json.loads(json.dumps(CFG)); bad["variables"][0]["direction"] = "sideways"
    with pytest.raises(ValueError):
        validate_config(bad)


def test_sensitivity_deterministic_and_sane():
    df = frame(200)
    a = run_sensitivity(df, CFG, n_draws=20, seed=1); b = run_sensitivity(df, CFG, n_draws=20, seed=1)
    assert a == b and a["computable"]
    assert 0.5 < a["spearman_vs_baseline"]["mean"] <= 1.0 and 0 < a["top_decile_jaccard"]["mean"] <= 1
    assert set(a["leave_one_out"]) == set(CFG_USED := [v["name"] for v in CFG["variables"]])


def test_normalise_percentile_clipping():
    s = pd.Series(list(range(100)) + [10_000])
    n, st = normalise(s, 2, 98)
    assert n.max() == 1.0 and n.min() == 0.0 and st["hi"] < 200  # outlier does not dominate the scale


def test_label_audit_defaults_to_index_without_labels(dirs):
    r = audit()
    assert r["active_path"] == "B" and r["supervised_model_trained"] is False


def test_label_audit_rejects_insufficient_or_undocumented(dirs):
    d, _ = dirs
    ld = d / "raw" / "flood_labels"; ld.mkdir(parents=True)
    (ld / "x.provenance.json").write_text(json.dumps({"n_positive": 12, "label_type": "verified_flood_observation"}))
    assert audit()["active_path"] == "B"
    full = {"event": "e", "observation_date": "d", "method": "m", "licence": "l", "source_url": "u", "crs": "c",
            "label_type": "satellite_water_mask_unverified", "n_positive": 5000}
    (ld / "x.provenance.json").write_text(json.dumps(full))
    assert audit()["active_path"] == "B", "unverified water masks must not enable supervised path"
    full["label_type"] = "verified_flood_observation"
    (ld / "x.provenance.json").write_text(json.dumps(full))
    assert audit()["active_path"] == "A"
