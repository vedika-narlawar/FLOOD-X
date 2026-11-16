# Methodology
**Path B — screening index** (selected by `pipeline/modeling/label_audit.py`; criteria: provenance sidecar + ≥100 verified positives).
`score = 100·Σ w_k n_k / Σ w_k` over variables available per cell (≥3 required, else NaN). `n_k` = percentile (P2–P98) min–max, inverted for "decrease" variables. Categories = equal-count quintiles (relative; ~20% of cells are "Very high" by construction).
Variables/weights (`configs/susceptibility_index.json`, expert-judgement priors, **uncalibrated**): relative elevation 0.25, slope 0.20, waterway distance 0.20, built-up share 0.20, elevation 0.15. Flow accumulation and rainfall deliberately excluded (reasons in config).
Missing inputs: excluded and weights renormalised per cell, reported via `n_inputs_used`; constant variables are skipped; contributions of absent inputs are NaN. Contributions decompose the score exactly.
Sensitivity (`pipeline/modeling/sensitivity.py`): 300 random weight perturbations (×U(0.5,1.5)), Spearman and top-decile Jaccard vs baseline, leave-one-out. This tests robustness to weighting, **not** validity against real floods.
Scenarios: only weights are applied. Rainfall multiplier/window are recorded but explicitly *not applied* because the index has no rainfall–runoff relation.
Exposure: cell-category sums of OSM facilities, road length (UTM) and WorldPop population — "potentially exposed to susceptibility", not flooded or damaged.
