import json

import pandas as pd
import pytest

from pipeline.common import DownloadError, download_file
from pipeline.ingestion.osm import facilities_to_points, overpass_to_gdf
from pipeline.ingestion.rainfall import parse_openmeteo, rolling_accumulations


def test_download_success_and_idempotent(tmp_path, server):
    p = tmp_path / "a.bin"
    r = download_file(f"{server}/ok", p, min_bytes=100)
    assert r["bytes"] == 5000 and not r["skipped_existing"] and len(r["sha256"]) == 64
    r2 = download_file(f"{server}/ok", p, min_bytes=100)
    assert r2["skipped_existing"]


def test_gzip_content_length_not_flagged_truncated(tmp_path, server):
    """Regression: Content-Length is the compressed size; decoded size must not trigger a false truncation error."""
    p = tmp_path / "g.bin"
    r = download_file(f"{server}/gz", p, min_bytes=100, retries=1)
    assert r["bytes"] == 32000


def test_truncated_download_rejected_and_valid_file_preserved(tmp_path, server):
    p = tmp_path / "keep.bin"
    p.write_bytes(b"valid" * 1000)
    with pytest.raises(DownloadError):
        download_file(f"{server}/truncated", p, min_bytes=100, retries=1, force=True)
    assert p.read_bytes() == b"valid" * 1000, "valid file was overwritten by failed download"
    assert not list(tmp_path.glob("*.part"))


def test_http_404_and_tiny_file(tmp_path, server):
    with pytest.raises(DownloadError):
        download_file(f"{server}/missing", tmp_path / "x", retries=1)
    with pytest.raises(DownloadError):
        download_file(f"{server}/tiny", tmp_path / "y", min_bytes=100, retries=1)


def test_dns_failure_fails_fast(tmp_path):
    import time
    t = time.time()
    with pytest.raises(DownloadError):
        download_file("https://does-not-exist.invalid/x", tmp_path / "z", retries=4)
    assert time.time() - t < 10


OVERPASS = {"elements": [
    {"type": "way", "id": 1, "geometry": [{"lat": 18.5, "lon": 73.8}, {"lat": 18.51, "lon": 73.81}], "tags": {"waterway": "stream"}},
    {"type": "way", "id": 1, "geometry": [{"lat": 18.5, "lon": 73.8}, {"lat": 18.51, "lon": 73.81}], "tags": {"waterway": "stream"}},  # duplicate
    {"type": "node", "id": 2, "lat": 18.52, "lon": 73.82, "tags": {"amenity": "hospital", "name": "H"}},
    {"type": "way", "id": 3, "center": {"lat": 18.53, "lon": 73.83}, "geometry": [{"lat": 18.53, "lon": 73.83}, {"lat": 18.531, "lon": 73.831}, {"lat": 18.53, "lon": 73.831}], "tags": {"amenity": "school"}},
    {"type": "relation", "id": 4, "tags": {}},  # no geometry -> skipped
    {"type": "way", "id": 5, "geometry": [{"lat": 18.5, "lon": 73.8}], "tags": {}},  # single point way -> skipped
]}


def test_overpass_parse_dedup_and_skips():
    g = overpass_to_gdf(OVERPASS)
    assert len(g) == 3 and g.crs.to_epsg() == 4326
    assert g["osm_id"].is_unique


def test_facilities_to_points_all_points():
    g = facilities_to_points(overpass_to_gdf(OVERPASS))
    assert (g.geom_type == "Point").all()


def test_overpass_empty():
    assert len(overpass_to_gdf({"elements": []})) == 0


def _om(vals, times=None):
    t = times or pd.date_range("2019-09-24", periods=len(vals), freq="h").strftime("%Y-%m-%dT%H:%M").tolist()
    return {"latitude": 18.5, "longitude": 73.8, "timezone": "Asia/Kolkata", "hourly_units": {"precipitation": "mm"},
            "hourly": {"time": t, "precipitation": vals}}


def test_openmeteo_parse_missing_and_units():
    df = parse_openmeteo(_om([0, 1.5, None, 2]), product="p", kind="historical_reanalysis", retrieved_at="t")
    assert df["missing"].tolist() == [False, False, True, False] and df.attrs["units"] == "mm"


def test_openmeteo_rejects_negative_and_malformed():
    with pytest.raises(ValueError):
        parse_openmeteo(_om([0, -1]), product="p", kind="k", retrieved_at="t")
    from pipeline.common import SourceUnavailable
    with pytest.raises(SourceUnavailable):
        parse_openmeteo({"error": True, "reason": "limit"}, product="p", kind="k", retrieved_at="t")


def test_rolling_accumulation_is_trailing_and_gap_aware():
    df = parse_openmeteo(_om([1, 1, 1, 1, None, 1, 1, 1]), product="p", kind="k", retrieved_at="t")
    acc = rolling_accumulations(df, windows=(3,))["acc_3h_mm"].tolist()
    assert pd.isna(acc[0]) and pd.isna(acc[1])  # not enough history: never uses future hours
    assert acc[2] == 3 and acc[3] == 3
    assert pd.isna(acc[4]) and pd.isna(acc[5]) and pd.isna(acc[6])  # window contains the gap -> NaN, not a silent partial sum
    assert acc[7] == 3
