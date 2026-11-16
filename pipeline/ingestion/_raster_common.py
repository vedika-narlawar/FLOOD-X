from __future__ import annotations

from pathlib import Path

import geopandas as gpd

from .. import registry
from ..common import data_dir
from ..validation.raster import validate_raster


def study_bounds_wgs84() -> tuple[float, float, float, float]:
    p = data_dir() / "interim" / "study_area.gpkg"
    if not p.exists():
        from ..common import Blocked
        raise Blocked("study_area.gpkg missing; run the 'study_area' stage first", ["study_area"])
    return tuple(gpd.read_file(p).to_crs(4326).total_bounds)


def finish_raster_dataset(ds_id: str, path: Path, info: dict, **vkw) -> dict:
    registry.update(ds_id, status="downloaded", local_path=str(path), sha256=info["sha256"],
                    retrieved_at=info["retrieved_at"], retrieval={"state": "ok", "bytes": info["bytes"]},
                    history=f"downloaded sha256={info['sha256'][:12]}")
    rep = validate_raster(path, study_bounds_wgs84(), **vkw)
    registry.update(ds_id, status="parsed" if rep["checks"][0]["passed"] else "rejected",
                    parse={"state": "ok" if rep["checks"][0]["passed"] else "failed", **rep["info"]})
    cov = next((c for c in rep["checks"] if c["check"] == "covers_study_area"), None)
    final = "ready_for_analysis" if rep["passed"] else "rejected"
    registry.update(ds_id, status=final, pune_overlap={"state": "ok" if cov and cov["passed"] else "failed",
                    "detail": cov["detail"] if cov else None}, quality_checks=rep["checks"],
                    history="raster validation executed")
    if not rep["passed"]:
        raise ValueError(f"{ds_id} rejected: {[c for c in rep['checks'] if not c['passed']]}")
    return rep
