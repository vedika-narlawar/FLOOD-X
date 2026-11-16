from __future__ import annotations

import hashlib
import json

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from pipeline.modeling.index import compute_index, load_config, with_weights

from ..schemas.scenario import ScenarioRequest


def evaluate(df: pd.DataFrame, req: ScenarioRequest, zone_col: str = "ward_name") -> dict:
    cfg = load_config()
    cfg_s = with_weights(cfg, req.weights) if req.weights else cfg
    base, binfo = compute_index(df, cfg)
    if not binfo["computable"]:
        raise ValueError(binfo["reason"])
    scen, sinfo = compute_index(df, cfg_s)
    m = base["score"].notna() & scen["score"].notna()
    rho = float(spearmanr(base.loc[m, "score"], scen.loc[m, "score"]).statistic) if m.sum() > 2 else None
    changed = int((base.loc[m, "category"] != scen.loc[m, "category"]).sum())

    def zone_rank(s):
        z = pd.DataFrame({"z": df[zone_col], "s": s["score"]}).dropna().groupby("z")["s"].mean()
        return z.rank(ascending=False, method="min")

    rb, rs = zone_rank(base), zone_rank(scen)
    tab = pd.DataFrame({"baseline_rank": rb, "scenario_rank": rs}).dropna().astype(int)
    tab["rank_change"] = tab["baseline_rank"] - tab["scenario_rank"]  # positive = moved up in susceptibility rank
    tab = tab.sort_values("scenario_rank").head(req.top_n).reset_index().rename(columns={"z": "zone"})
    hist = lambda s: np.histogram(s.dropna(), bins=np.linspace(0, 100, 11))[0].tolist()
    applied_w = {v["name"]: v["weight"] for v in cfg_s["variables"]}
    cfg_echo = req.model_dump()
    return {
        "scenario_id": hashlib.sha256(json.dumps(cfg_echo, sort_keys=True).encode()).hexdigest()[:12],
        "configuration": cfg_echo,
        "type": "hypothetical_weight_scenario",
        "not_a_forecast": True,
        "applied": {"weights": applied_w, "normalised_weights": {k: v / sum(applied_w.values()) for k, v in applied_w.items()}},
        "not_applied": [{"parameter": "rainfall_multiplier / window_hours",
                         "reason": "The screening index is a static terrain/land-cover/waterway index; it has no rainfall-runoff or drainage "
                                   "relationship, so rainfall changes cannot be translated into scores, flood depth or extent without inventing one."}],
        "assumptions": ["Scores recomputed with the same percentile normalisation as the baseline",
                        "Only index weights differ between baseline and scenario",
                        "Outputs are relative screening scores, not observed flood extents or forecasts"],
        "comparison": {"n_cells_compared": int(m.sum()), "spearman_rank_correlation": rho,
                       "cells_changing_category": changed,
                       "score_histogram_bins_0_100": {"baseline": hist(base["score"]), "scenario": hist(scen["score"])},
                       "mean_score": {"baseline": float(base["score"].mean()), "scenario": float(scen["score"].mean())},
                       "zone_ranking": tab.to_dict(orient="records")},
    }
