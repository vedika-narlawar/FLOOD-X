"""Runs the REAL pipeline code on a SYNTHETIC site to prove the chain works when data is available.
Nothing here is production data and nothing from here is ever written to data/ or artifacts/."""
import geopandas as gpd
import numpy as np
import pandas as pd
import pytest

from pipeline.exposure import analysis as exposure
from pipeline.features import build
from pipeline.inference import susceptibility
from pipeline.preprocessing import grid, study_area


@pytest.fixture
def built(synth_site):
    d, a = synth_site
    study_area.run()
    grid.run(cell_m=500.0)
    build.terrain_stage()
    build.run()
    susceptibility.run()
    exposure.run()
    return d, a


def test_study_area_and_grid(built):
    d, _ = built
    sa = gpd.read_file(d / "interim" / "study_area.gpkg")
    assert int(sa.utm_epsg.iloc[0]) == 32643 and 15 < sa.area_km2.iloc[0] < 22  # ~4x4.3 km box
    g = gpd.read_file(d / "processed" / "grid.gpkg")
    assert g.crs.to_epsg() == 32643 and g.ward_id.notna().all() and g.cell_id.is_unique
    assert g.clipped_area_m2.sum() == pytest.approx(sa.area_km2.iloc[0] * 1e6, rel=0.02)


def test_features_computed_with_expected_physics(built):
    d, _ = built
    f = gpd.read_parquet(d / "processed" / "features" / "grid_features.parquet")
    man = pd.read_json(d / "processed" / "features" / "feature_manifest.json")["features"]
    avail = {k for k, v in man.items() if v["status"] == "available"}
    assert {"elev_mean_m", "slope_mean_deg", "rel_elev_mean_m", "builtup_share", "population_sum", "dist_waterway_m", "road_length_m", "n_school"} <= avail
    assert man["flow_accumulation"]["status"] == "unavailable"
    # built-up (west) vs grass (east): west cells have higher built-up share
    c = f.geometry.centroid.to_crs(4326)
    assert f.loc[c.x < 73.82, "builtup_share"].mean() > 0.8 > 0.2 > f.loc[c.x > 73.82, "builtup_share"].mean()
    # elevation ramp rises eastward (800 m per degree)
    assert f.loc[c.x > 73.82, "elev_mean_m"].mean() > f.loc[c.x < 73.82, "elev_mean_m"].mean() + 10
    # nodata hole in population raster is outside the study box, but totals must be positive and finite
    assert np.isfinite(f["population_sum"]).all() and (f["population_sum"] >= 0).all()
    assert f["dist_waterway_m"].min() >= 0
    assert int(f[["n_hospital"]].sum().iloc[0]) == 1 and int(f["n_school"].sum()) == 2
    assert man["n_clinic"]["status"] == "available" and f["n_clinic"].sum() == 0  # zero is meaningful: layer exists, none mapped


def test_index_outputs_and_layers(built):
    _, a = built
    g = gpd.read_file(a / "layers" / "susceptibility_grid.geojson")
    assert g.crs.to_epsg() == 4326 and g["score"].between(0, 100).all()
    z = gpd.read_file(a / "layers" / "susceptibility_zones.geojson")
    assert len(z) == 4 and z["score_mean"].notna().all()
    import json
    meta = json.loads((a / "layers" / "susceptibility_metadata.json").read_text())
    assert meta["output_semantics"].startswith("relative screening score") and meta["limitations"]
    sens = json.loads((a / "metrics" / "sensitivity.json").read_text())
    assert sens["computable"]


def test_exposure_sums_match_inputs(built):
    _, a = built
    import json
    s = json.loads((a / "layers" / "exposure_summary.json").read_text())
    fac = s["sections"]["facilities"]["by_category"]
    assert sum(v["n_school"] for v in fac.values()) == 2 and sum(v["n_hospital"] for v in fac.values()) == 1
    pop = s["sections"]["population"]
    assert pop["status"] == "available" and pop["total"] > 0
    assert "not flooded" in s["caveat"].lower() or "!= flooded" in s["caveat"]
    fgj = gpd.read_file(a / "layers" / "exposure_facilities.geojson")
    assert len(fgj) == 3 and fgj["category"].notna().all()


def test_missing_inputs_are_blocked_not_faked(dirs):
    from pipeline.common import Blocked
    with pytest.raises(Blocked):
        study_area.run()
    with pytest.raises(Blocked):
        susceptibility.run()
    with pytest.raises(Blocked):
        exposure.run()
    with pytest.raises(Blocked):
        build.terrain_stage()


def test_blocked_index_removes_stale_outputs(synth_site):
    d, a = synth_site
    study_area.run(); grid.run(); build.terrain_stage(); build.run(); susceptibility.run()
    assert (a / "layers" / "susceptibility_grid.geojson").exists()
    for p in (d / "raw" / "dem").glob("*.tif"):
        p.unlink()
    for sub in ("landcover", "population"):
        for p in (d / "raw" / sub).glob("*.tif"):
            p.unlink()
    for p in (d / "interim").glob("osm_*.gpkg"):
        p.unlink()
    for p in (d / "processed" / "terrain").glob("*.tif"):
        p.unlink()
    from pipeline.common import Blocked
    try:
        build.run()
    except Blocked:
        pass
    with pytest.raises(Blocked):
        susceptibility.run()
    assert not (a / "layers" / "susceptibility_grid.geojson").exists(), "stale layer would be served as current"


def test_optional_pcmc_extends_study_area_without_id_collisions(synth_site):
    """SYNTHETIC PCMC polygons next to the synthetic PMC site: union grows and ward ids stay unique."""
    from shapely.geometry import box
    d, _ = synth_site
    gpd.GeoDataFrame({"name": ["a", "b"], "zone": ["z", "z"], "wardnum": ["1", "2"]},
                     geometry=[box(73.84, 18.50, 73.86, 18.52), box(73.84, 18.52, 73.86, 18.54)], crs=4326).to_file(d / "interim" / "boundaries_pcmc_wards.gpkg", driver="GPKG")
    study_area.run(); grid.run()
    sa = gpd.read_file(d / "interim" / "study_area.gpkg")
    assert "PCMC" in sa["name"].iloc[0] and sa.area_km2.iloc[0] > 20
    w = gpd.read_file(d / "interim" / "wards_utm.gpkg")
    assert w.ward_id.is_unique and set(w.municipality) == {"PMC", "PCMC"} and (w[w.municipality == "PCMC"].ward_id > 1000).all()
    g = gpd.read_file(d / "processed" / "grid.gpkg")
    assert g.ward_id.notna().all() and (g.ward_id > 1000).any()
