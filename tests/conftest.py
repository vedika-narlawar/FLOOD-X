"""SYNTHETIC FIXTURES LIVE ONLY IN tests/. They never touch production data dirs."""
from __future__ import annotations

import gzip
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import geopandas as gpd
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import box

SYN_BOX = (73.80, 18.50, 73.84, 18.54)  # synthetic 'study area' inside Pune (lon/lat)


@pytest.fixture
def dirs(tmp_path, monkeypatch):
    d, a = tmp_path / "data", tmp_path / "artifacts"
    for p in (d / "raw", d / "interim", d / "processed", d / "registry", a / "layers", a / "models", a / "metrics"):
        p.mkdir(parents=True)
    monkeypatch.setenv("FLOODX_DATA_DIR", str(d))
    monkeypatch.setenv("FLOODX_ARTIFACTS_DIR", str(a))
    return d, a


class _H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path == "/ok":
            body = b"x" * 5000
            self.send_response(200); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
        elif self.path == "/gz":  # Content-Length is the COMPRESSED size (regression test)
            raw = (b"abcdefgh" * 4000)
            body = gzip.compress(raw)
            self.send_response(200); self.send_header("Content-Encoding", "gzip"); self.send_header("Content-Length", str(len(body)))
            self.end_headers(); self.wfile.write(body)
        elif self.path == "/truncated":
            self.send_response(200); self.send_header("Content-Length", "10000"); self.end_headers(); self.wfile.write(b"y" * 1000)
            self.wfile.flush(); self.close_connection = True
        elif self.path == "/tiny":
            self.send_response(200); self.send_header("Content-Length", "3"); self.end_headers(); self.wfile.write(b"abc")
        else:
            self.send_response(404); self.send_header("Content-Length", "0"); self.end_headers()


@pytest.fixture(scope="session")
def server():
    s = HTTPServer(("127.0.0.1", 0), _H)
    t = threading.Thread(target=s.serve_forever, daemon=True); t.start()
    yield f"http://127.0.0.1:{s.server_port}"
    s.shutdown()


def write_raster(path, arr, bounds, crs="EPSG:4326", nodata=None, dtype="float32"):
    h, w = arr.shape
    tr = from_origin(bounds[0], bounds[3], (bounds[2] - bounds[0]) / w, (bounds[3] - bounds[1]) / h)
    with rasterio.open(path, "w", driver="GTiff", height=h, width=w, count=1, dtype=dtype, crs=crs, transform=tr, nodata=nodata) as d:
        d.write(arr.astype(dtype), 1)
    return path


@pytest.fixture
def synth_site(dirs):
    """Synthetic wards/study area/rasters/OSM in the tmp data dir (all clearly synthetic)."""
    d, a = dirs
    w, s, e, n = SYN_BOX
    xs = np.linspace(w, e, 3)
    ys = np.linspace(s, n, 3)
    wards = [box(xs[i], ys[j], xs[i + 1], ys[j + 1]) for i in range(2) for j in range(2)]
    wg = gpd.GeoDataFrame({"wardnum": [1, 2, 3, 4], "Name1": [f"SYN ward {i}" for i in range(1, 5)]}, geometry=wards, crs=4326)
    wg.to_file(d / "interim" / "boundaries_pmc_wards_2022.gpkg", driver="GPKG")
    # DEM tile (4326): plane rising west->east plus a low basin (relative depression) near the centre
    tb = (73.70, 18.40, 73.95, 18.65)
    n_ = 900
    xx, yy = np.meshgrid(np.linspace(tb[0], tb[2], n_), np.linspace(tb[3], tb[1], n_))
    dem = 560 + (xx - tb[0]) * 800 - ((xx - 73.82) ** 2 + (yy - 18.52) ** 2) ** 0.5 * 0 
    dem -= 15 * np.exp(-(((xx - 73.82) / 0.006) ** 2 + ((yy - 18.52) / 0.006) ** 2))
    (d / "raw" / "dem").mkdir(parents=True)
    write_raster(d / "raw" / "dem" / "SYN_dem.tif", dem, tb, nodata=-9999)
    # land cover: built-up (50) in west half, grass (30) in east half
    (d / "raw" / "landcover").mkdir(parents=True)
    lc = np.where(xx[::2, ::2] < 73.82, 50, 30).astype("uint8")
    write_raster(d / "raw" / "landcover" / "SYN_lc.tif", lc, tb, nodata=0, dtype="uint8")
    # population: 2 people per pixel with a nodata hole
    (d / "raw" / "population").mkdir(parents=True)
    pop = np.full((250, 250), 2.0, dtype="float32"); pop[:20, :20] = -99999
    write_raster(d / "raw" / "population" / "SYN_pop.tif", pop, tb, nodata=-99999)
    # OSM-like layers
    from shapely.geometry import LineString, Point
    gpd.GeoDataFrame({"waterway": ["stream"]}, geometry=[LineString([(73.81, 18.50), (73.815, 18.54)])], crs=4326).to_file(d / "interim" / "osm_waterways.gpkg", driver="GPKG")
    gpd.GeoDataFrame({"highway": ["primary", "residential"]}, geometry=[LineString([(73.80, 18.51), (73.84, 18.51)]), LineString([(73.82, 18.50), (73.82, 18.54)])], crs=4326).to_file(d / "interim" / "osm_roads.gpkg", driver="GPKG")
    gpd.GeoDataFrame({"amenity": ["hospital", "school", "school"], "name": ["h", "s1", "s2"]},
                     geometry=[Point(73.805, 18.505), Point(73.835, 18.535), Point(73.812, 18.52)], crs=4326).to_file(d / "interim" / "osm_facilities.gpkg", driver="GPKG")
    return d, a
