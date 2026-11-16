"""GIS-Based Flood Susceptibility Screening Index.

score_i = 100 * sum_k(w_k * n_ik) / sum_k(w_k)   over the variables available for cell i
n_ik   = percentile-min-max normalised value of variable k (inverted when direction == 'decrease')

Not a probability. Not calibrated. Missing inputs are excluded and weights renormalised per
cell; cells with fewer than `min_inputs` available variables get NaN (never an imputed value).
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import pandas as pd

from ..common import config_dir


def load_config(path: Path | None = None) -> dict:
    cfg = json.loads((path or config_dir() / "susceptibility_index.json").read_text())
    validate_config(cfg)
    return cfg


def validate_config(cfg: dict) -> None:
    names = [v["name"] for v in cfg["variables"]]
    if len(set(names)) != len(names):
        raise ValueError("duplicate variable names in index config")
    for v in cfg["variables"]:
        if v["direction"] not in ("increase", "decrease"):
            raise ValueError(f"bad direction for {v['name']}")
        if not (v["weight"] >= 0 and np.isfinite(v["weight"])):
            raise ValueError(f"weight must be finite and >= 0 for {v['name']}")
    if sum(v["weight"] for v in cfg["variables"]) <= 0:
        raise ValueError("weights sum to zero")


def with_weights(cfg: dict, weights: dict[str, float]) -> dict:
    unknown = set(weights) - {v["name"] for v in cfg["variables"]}
    if unknown:
        raise ValueError(f"unknown variables: {sorted(unknown)}")
    c = copy.deepcopy(cfg)
    for v in c["variables"]:
        if v["name"] in weights:
            v["weight"] = float(weights[v["name"]])
    validate_config(c)
    return c


def normalise(s: pd.Series, lo_pct: float, hi_pct: float) -> tuple[pd.Series, dict]:
    x = pd.to_numeric(s, errors="coerce")
    valid = x.dropna()
    if valid.empty:
        return x * np.nan, {"status": "no_valid_values"}
    lo, hi = np.percentile(valid, [lo_pct, hi_pct])
    if hi <= lo:
        return x * np.nan, {"status": "degenerate_no_variance", "lo": float(lo), "hi": float(hi)}
    return ((x.clip(lo, hi) - lo) / (hi - lo)), {"status": "ok", "lo": float(lo), "hi": float(hi)}


def compute_index(df: pd.DataFrame, cfg: dict, norm_stats: dict | None = None) -> tuple[pd.DataFrame, dict]:
    """Returns (scores_df, info). scores_df index == df.index.
    Columns: score, category, n_inputs_used, contrib_<var>. info lists used/skipped variables."""
    nz = cfg["normalization"]
    comps, used, skipped, stats = {}, [], [], {}
    for v in cfg["variables"]:
        if v["name"] not in df.columns:
            skipped.append({"name": v["name"], "reason": "column not present (feature unavailable)"})
            continue
        n, st = normalise(df[v["name"]], nz["lower_pct"], nz["upper_pct"])
        stats[v["name"]] = st
        if st["status"] != "ok":
            skipped.append({"name": v["name"], "reason": st["status"]})
            continue
        comps[v["name"]] = (1 - n) if v["direction"] == "decrease" else n
        used.append(v["name"])
    out = pd.DataFrame(index=df.index)
    info = {"variables_used": used, "variables_skipped": skipped, "normalisation": stats,
            "weights": {v["name"]: v["weight"] for v in cfg["variables"]}}
    if len(used) < cfg["min_inputs"]:
        out["score"] = np.nan
        out["category"] = None
        out["n_inputs_used"] = 0
        info["computable"] = False
        info["reason"] = f"only {len(used)} of required minimum {cfg['min_inputs']} variables available"
        return out, info
    w = pd.Series({v["name"]: v["weight"] for v in cfg["variables"] if v["name"] in used})
    N = pd.DataFrame(comps)
    avail = N.notna()
    wsum = avail.mul(w, axis=1).sum(axis=1)
    weighted = N.fillna(0).mul(w, axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        contrib = weighted.div(wsum.where(wsum > 0), axis=0) * 100
    contrib = contrib.where(avail)  # a missing input has NO contribution (NaN), never an implicit 0
    nused = avail.sum(axis=1)
    ok = nused >= cfg["min_inputs"]
    out["score"] = contrib.sum(axis=1).where(ok)
    out["n_inputs_used"] = nused.astype(int)
    for c in contrib.columns:
        out[f"contrib_{c}"] = contrib[c].where(ok)
    labels = cfg["categories"]["labels"]
    sc = out["score"].dropna()
    edges = np.quantile(sc, np.linspace(0, 1, len(labels) + 1)) if len(sc) else np.array([])
    if len(sc) and np.unique(edges).size == edges.size:
        out["category"] = pd.cut(out["score"], bins=edges, labels=labels, include_lowest=True).astype(object)
    else:
        out["category"] = None
        info["category_note"] = "quantile edges not unique; categories not assigned"
    info.update(computable=True, category_edges=[float(e) for e in edges], n_scored=int(ok.sum()), n_cells=int(len(df)))
    return out, info
