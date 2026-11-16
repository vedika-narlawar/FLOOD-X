"""Applies the screening index to the feature grid and writes frontend-ready layers."""
from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd

from ..common import Blocked, art_dir, data_dir, get_logger, now_iso, read_json, write_json_atomic
from ..modeling.index import compute_index, load_config
from ..modeling.sensitivity import run_sensitivity

log = get_logger("floodx.inference")
LIMITS = ["Relative screening score, not a flood probability, hazard, depth or inundation extent",
          "Weights are expert-judgement priors, not calibrated against observed floods",
          "Elevation is a surface model (buildings/canopy included) at 30 m",
          "Waterway layer from OSM omits many culverted channels", "Scores comparable only within this run (percentile-normalised)"]


def aggregate_zones(g: gpd.GeoDataFrame, wards: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    s = g.dropna(subset=["score"])
    high = s["category"].isin(["High", "Very high"])
    agg = s.assign(_hi=high).groupby("ward_id").agg(
        n_cells=("score", "size"), score_mean=("score", "mean"), score_p90=("score", lambda x: float(np.percentile(x, 90))),
        high_share=("_hi", "mean"), area_km2=("clipped_area_m2", lambda x: x.sum() / 1e6)).reset_index()
    # Exposure aggregates kept as separate columns (NaN when the underlying layer is absent - never 0)
    for col in ("population_sum", "road_length_m", "n_hospital", "n_clinic", "n_school", "n_fire_station", "n_police"):
        if col in g.columns and g[col].notna().any():
            agg = agg.merge(g.groupby("ward_id")[col].sum(min_count=1).rename(f"exp_{col}").reset_index(), on="ward_id", how="left")
    
    cc = [c for c in s.columns if c.startswith("contrib_")]
    if cc:
        # Average each existing grid-cell contribution within each ward.
        # Missing contributions are treated as zero to preserve the
        # model's existing contribution-summing convention.
        mc = s[cc].fillna(0).groupby(s["ward_id"]).mean()

        # Retain the dominant factor and expose every factor contribution.
        mc = mc.rename(
            columns=lambda c: f"{c}_mean"
        )
        mc = mc.rename(
            columns=lambda c: c.removesuffix("_mean").replace("contrib_", "contrib_mean_")
        )

        agg = agg.merge(
            mc.reset_index(),
            on="ward_id",
            how="left"
        )

        driver_cols = [
            c for c in agg.columns
            if c.startswith("contrib_mean_")
        ]
        if driver_cols:
            agg = agg.merge(
                agg[["ward_id"] + driver_cols]
                .set_index("ward_id")
                .idxmax(axis=1)
                .str.replace("contrib_mean_", "", regex=False)
                .rename("top_driver")
                .reset_index(),
                on="ward_id",
                how="left"
            )

    z = wards[["ward_id", "ward_name", "geometry"]].merge(agg, on="ward_id", how="left")
    z["rank_by_mean"] = z["score_mean"].rank(ascending=False, method="min")
    return z


def run() -> list[str]:
    fp = data_dir() / "processed" / "features" / "grid_features.parquet"
    if not fp.exists():
        raise Blocked("feature grid missing", ["grid_features"])
    g = gpd.read_parquet(fp)
    cfg = load_config()
    scores, info = compute_index(pd.DataFrame(g.drop(columns="geometry")), cfg)
    if not info["computable"]:
        # Remove any stale outputs so the API cannot serve results from an older, different run
        for p in (art_dir() / "layers").glob("susceptibility_*"):
            p.unlink()
        raise Blocked(f"Susceptibility index not computable: {info['reason']}. Skipped: "
                      f"{[s['name'] + ' (' + s['reason'] + ')' for s in info['variables_skipped']]}",
                      [s["name"] for s in info["variables_skipped"]])
    out = g.join(scores)
    layers = art_dir() / "layers"
    layers.mkdir(parents=True, exist_ok=True)
    out.to_file(layers / "susceptibility_grid.gpkg", driver="GPKG")
    out.to_crs(4326).to_file(layers / "susceptibility_grid.geojson", driver="GeoJSON")
    wards = gpd.read_file(data_dir() / "interim" / "wards_utm.gpkg")
    zones = aggregate_zones(out, wards)
    zones.to_crs(4326).to_file(layers / "susceptibility_zones.geojson", driver="GeoJSON")
    sens = run_sensitivity(pd.DataFrame(g.drop(columns="geometry")), cfg)
    write_json_atomic(art_dir() / "metrics" / "sensitivity.json", sens)
    manifest = read_json(data_dir() / "processed" / "features" / "feature_manifest.json", {})
    meta = {"generated_at": now_iso(), "method": cfg["name"], "version": cfg["version"], "output_semantics": cfg["output"],
            "crs_analysis": str(g.crs), "crs_delivery": "EPSG:4326", "cell_size_m": 500, "config": cfg,
            "variables_used": info["variables_used"], "variables_skipped": info["variables_skipped"],
            "category_edges": info["category_edges"], "n_scored": info["n_scored"], "n_cells": info["n_cells"],
            "input_datasets": sorted({manifest.get("features", {}).get(v, {}).get("source_dataset", "?") for v in info["variables_used"]}),
            "feature_manifest": manifest.get("features", {}), "limitations": LIMITS,
            "mean_contribution": {c.replace("contrib_", ""): float(out.loc[out["score"].notna(), c].fillna(0).mean())
                                  for c in out.columns if c.startswith("contrib_")},
            "mean_contribution_note": "Averaged over all scored cells; an absent input contributes 0 to that cell's sum, so contributions sum exactly to the mean score."}
    write_json_atomic(layers / "susceptibility_metadata.json", meta)
    return [str(p) for p in layers.glob("susceptibility_*")]
