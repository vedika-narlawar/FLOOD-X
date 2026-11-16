"""Sensitivity analysis for the screening index: random weight perturbation and leave-one-out."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from .index import compute_index, with_weights


def run_sensitivity(df: pd.DataFrame, cfg: dict, n_draws: int = 300, rel_range: float = 0.5, seed: int = 42,
                    top_frac: float = 0.10) -> dict:
    rng = np.random.default_rng(seed)
    base, info = compute_index(df, cfg)
    if not info["computable"]:
        return {"computable": False, "reason": info["reason"]}
    used = info["variables_used"]
    b = base["score"]
    mask = b.notna()
    k = max(1, int(round(top_frac * mask.sum())))
    top_base = set(b[mask].nlargest(k).index)
    rhos, jacc, ranks = [], [], []
    for _ in range(n_draws):
        f = rng.uniform(1 - rel_range, 1 + rel_range, size=len(used))
        w = {n: info["weights"][n] * fi for n, fi in zip(used, f)}
        s, _ = compute_index(df, with_weights(cfg, w))
        s = s["score"]
        rhos.append(spearmanr(b[mask], s[mask]).statistic)
        top = set(s[mask].nlargest(k).index)
        jacc.append(len(top & top_base) / len(top | top_base))
        ranks.append(s[mask].rank(ascending=False).values)
    R = np.vstack(ranks)
    base_rank = b[mask].rank(ascending=False).values
    loo = {}
    for n in used:
        w = {m: (0.0 if m == n else info["weights"][m]) for m in used}
        if sum(w.values()) <= 0:
            continue
        s, _ = compute_index(df, with_weights(cfg, w))
        s = s["score"]
        m2 = s.notna() & mask
        loo[n] = {"spearman_vs_baseline": float(spearmanr(b[m2], s[m2]).statistic),
                  "top_decile_jaccard": float(len(set(s[m2].nlargest(k).index) & top_base) / len(set(s[m2].nlargest(k).index) | top_base))}
    return {"computable": True, "seed": seed, "n_draws": n_draws, "weight_perturbation": f"each weight x U({1-rel_range}, {1+rel_range})",
            "n_cells": int(mask.sum()), "top_fraction": top_frac,
            "spearman_vs_baseline": {"mean": float(np.mean(rhos)), "min": float(np.min(rhos)), "p5": float(np.percentile(rhos, 5))},
            "top_decile_jaccard": {"mean": float(np.mean(jacc)), "min": float(np.min(jacc)), "p5": float(np.percentile(jacc, 5))},
            "rank_width_p5_p95": {"median_cells": float(np.median(np.percentile(R, 95, axis=0) - np.percentile(R, 5, axis=0))),
                                  "n_cells": int(mask.sum())},
            "leave_one_out": loo,
            "interpretation": "High Spearman/Jaccard means rankings are robust to the weighting choice; this does NOT validate the index against observed floods."}
