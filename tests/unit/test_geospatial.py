import geopandas as gpd
import numpy as np
import pytest
import rasterio
from shapely.geometry import Polygon, box

from pipeline.features import terrain
from pipeline.features.zonal import zonal_class_share, zonal_mean, zonal_sum
from pipeline.geo import study_utm, utm_epsg_for
from pipeline.validation.raster import validate_raster
from pipeline.validation.vector import repair_geometries, validate_vector
from tests.conftest import SYN_BOX, write_raster


def test_utm_zone_for_pune():
    assert utm_epsg_for(73.86, 18.52) == 32643


def test_area_in_utm_not_degrees():
    g = gpd.GeoDataFrame(geometry=[box(73.80, 18.50, 73.81, 18.51)], crs=4326)
    km2 = g.to_crs(study_utm(g)).area.iloc[0] / 1e6
    assert 1.0 < km2 < 1.2  # ~1.05 km2 (0.01 deg ~ 1.05 km x 1.1 km); degrees^2 would be 1e-4
    assert g.geometry.area.iloc[0] < 1e-3


def test_vector_validation_flags_problems():
    bow = Polygon([(73.8, 18.5), (73.82, 18.52), (73.82, 18.5), (73.8, 18.52)])  # self-intersecting
    g = gpd.GeoDataFrame(geometry=[bow], crs=4326)
    rep = validate_vector(g)
    assert not rep["passed"] and any(c["check"] == "valid_geometry" and not c["passed"] for c in rep["checks"])
    fixed, n = repair_geometries(g)
    assert n == 1 and fixed.geometry.is_valid.all()


def test_vector_validation_rejects_chennai_coordinates():
    g = gpd.GeoDataFrame(geometry=[box(80.2, 13.0, 80.3, 13.1)], crs=4326)  # Chennai
    rep = validate_vector(g)
    assert not rep["passed"] and any(c["check"] == "within_pune_window" and not c["passed"] for c in rep["checks"])


def test_vector_validation_duplicates_and_no_crs():
    b = box(73.8, 18.5, 73.81, 18.51)
    assert any(c["check"] == "no_duplicate_geometries" and not c["passed"] for c in validate_vector(gpd.GeoDataFrame(geometry=[b, b], crs=4326))["checks"])
    assert not validate_vector(gpd.GeoDataFrame(geometry=[b]))["passed"]


def test_raster_validation_ok_and_nodata(tmp_path):
    a = np.full((100, 100), 600.0, dtype="float32"); a[:50] = -9999
    p = write_raster(tmp_path / "r.tif", a, (73.7, 18.4, 73.95, 18.65), nodata=-9999)
    rep = validate_raster(p, SYN_BOX, min_valid_fraction=0.4)
    assert rep["passed"] and abs(rep["info"]["valid_fraction_sampled"] - 0.5) < 0.05
    assert not validate_raster(p, SYN_BOX, min_valid_fraction=0.8)["passed"]


def test_raster_validation_coverage_and_malformed(tmp_path):
    a = np.ones((10, 10), dtype="float32")
    p = write_raster(tmp_path / "small.tif", a, (73.0, 18.0, 73.1, 18.1))
    assert any(c["check"] == "covers_study_area" and not c["passed"] for c in validate_raster(p, SYN_BOX)["checks"])
    bad = tmp_path / "bad.tif"; bad.write_bytes(b"not a tiff at all" * 50)
    rep = validate_raster(bad, SYN_BOX)
    assert not rep["passed"] and rep["checks"][0]["check"] == "readable" and not rep["checks"][0]["passed"]
    trunc = tmp_path / "trunc.tif"; trunc.write_bytes(p.read_bytes()[:40])
    assert not validate_raster(trunc, SYN_BOX)["passed"]


def test_value_range_check(tmp_path):
    p = write_raster(tmp_path / "neg.tif", np.full((10, 10), -5.0, dtype="float32"), (73.7, 18.4, 73.95, 18.65))
    assert not validate_raster(p, SYN_BOX, value_range=(0, 1e6))["passed"]


def test_zonal_stats_respect_nodata_and_masks(tmp_path):
    # UTM raster, 10 m pixels: left half value 10, right half value 20, a nodata corner
    arr = np.zeros((100, 100), dtype="float32"); arr[:, :50] = 10; arr[:, 50:] = 20; arr[:10, :10] = -1
    p = write_raster(tmp_path / "u.tif", arr, (400000, 2000000, 401000, 2001000), crs="EPSG:32643", nodata=-1)
    left = gpd.GeoDataFrame(geometry=[box(400000, 2000000, 400500, 2001000)], crs=32643)
    right = gpd.GeoDataFrame(geometry=[box(400500, 2000000, 401000, 2001000)], crs=32643)
    assert zonal_mean(p, left).iloc[0] == pytest.approx(10.0)
    assert zonal_mean(p, right).iloc[0] == pytest.approx(20.0)
    assert zonal_sum(p, right).iloc[0] == pytest.approx(20.0 * 5000)
    outside = gpd.GeoDataFrame(geometry=[box(500000, 2000000, 500500, 2001000)], crs=32643)
    assert np.isnan(zonal_mean(p, outside).iloc[0]), "no overlap must be NaN, not zero"
    lc = np.where(np.arange(100)[None, :] < 25, 50, 30).astype("uint8") * np.ones((100, 1), dtype="uint8")
    q = write_raster(tmp_path / "lc.tif", lc, (400000, 2000000, 401000, 2001000), crs="EPSG:32643", nodata=0, dtype="uint8")
    assert zonal_class_share(q, left, {50}).iloc[0] == pytest.approx(0.5, abs=0.01)


def test_slope_of_plane_is_exact():
    res = 30.0
    x = np.arange(50) * res
    plane = np.tile(x * 0.1, (50, 1)).astype("float32")  # rise 0.1 per metre east
    s = terrain.slope_degrees(plane, res)
    assert np.allclose(s[5:-5, 5:-5], np.degrees(np.arctan(0.1)), atol=1e-3)


def test_relative_elevation_negative_in_depression_and_nan_aware():
    z = np.full((60, 60), 100.0, dtype="float32"); z[28:32, 28:32] = 90
    rel = terrain.relative_elevation(z, 30.0, radius_m=300)
    assert rel[30, 30] < -5 and abs(rel[5, 5]) < 1e-3
    z[:, :20] = np.nan
    rel2 = terrain.relative_elevation(z, 30.0, radius_m=300)
    assert np.isnan(rel2[10, 5]) and np.isfinite(rel2[30, 40])


def test_mosaic_to_utm_preserves_elevation(synth_site):
    import glob
    d, _ = synth_site
    from pathlib import Path
    tiles = [Path(p) for p in glob.glob(str(d / "raw" / "dem" / "*.tif"))]
    elev, tr = terrain.mosaic_to_utm(tiles, SYN_BOX, 32643, 30.0)
    assert np.isfinite(elev).mean() > 0.9
    # synthetic ramp: 560 + 800*(lon-73.70); at lon 73.82 -> 656
    assert 640 < np.nanmedian(elev) < 680
