"""Read-only access to pipeline outputs. Never fabricates: absent files raise Unavailable with the
upstream pipeline reason attached."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import geopandas as gpd
import pandas as pd

from pipeline import registry
from pipeline import status as pstatus
from pipeline.common import art_dir, data_dir, read_json


class Unavailable(Exception):
    def __init__(self, module: str, reason: str, blocking_stages: list[str] | None = None):
        super().__init__(reason)
        self.module, self.reason, self.blocking_stages = module, reason, blocking_stages or []

    def detail(self) -> dict:
        led = pstatus.load()["stages"]
        upstream = {s: {"status": led.get(s, {}).get("status", "pending"), "message": led.get(s, {}).get("message", "not run")}
                    for s in self.blocking_stages}
        return {"status": "unavailable", "module": self.module, "reason": self.reason, "upstream_stages": upstream,
                "see": "/api/pipeline/status"}


def _key(p: Path):
    return (str(p), p.stat().st_mtime_ns) if p.exists() else (str(p), None)


@lru_cache(maxsize=32)
def _gdf(path: str, mtime):
    return gpd.read_file(path)


@lru_cache(maxsize=32)
def _gpq(path: str, mtime):
    return gpd.read_parquet(path)


def read_gdf(p: Path) -> gpd.GeoDataFrame:
    return _gdf(*_key(p))


def read_features() -> pd.DataFrame:
    p = data_dir() / "processed" / "features" / "grid_features.parquet"
    if not p.exists():
        raise Unavailable("features", "Feature grid not generated.", ["grid_features", "terrain", "download_dem"])
    return _gpq(*_key(p))


def feature_manifest() -> dict | None:
    return read_json(data_dir() / "processed" / "features" / "feature_manifest.json")


def layer(name: str) -> Path:
    return art_dir() / "layers" / name


def require_layer(name: str, module: str, stages: list[str], reason: str) -> Path:
    p = layer(name)
    if not p.exists():
        raise Unavailable(module, reason, stages)
    return p


def registry_all() -> dict:
    return registry.load()["datasets"]
