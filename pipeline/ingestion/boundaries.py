"""Pune boundary ingestion (DataMeet). This stage runs for real in restricted environments
because raw.githubusercontent.com is reachable."""
from __future__ import annotations

import geopandas as gpd

from .. import registry
from ..common import data_dir, download_file, get_logger
from ..validation.vector import repair_geometries, validate_vector

log = get_logger("floodx.boundaries")
TARGETS = {"boundaries_pmc_wards_2022": ("pune-electoral-wards_2022.geojson", 58),
           "boundaries_pmc_admin_wards_2017": ("pune-admin-wards_2017.geojson", 15),
           "boundaries_pcmc_wards": ("pcmc-electoral-wards.geojson", 66)}


def run(force: bool = False) -> list[str]:
    outs = []
    for ds_id, (fname, expected_n) in TARGETS.items():
        ds = registry.load()["datasets"][ds_id]
        raw = data_dir() / "raw" / "boundaries" / fname
        info = download_file(ds["source_url"], raw, min_bytes=1000, force=force)
        registry.update(ds_id, status="downloaded", local_path=str(raw), sha256=info["sha256"],
                        retrieved_at=info["retrieved_at"] or ds.get("retrieved_at"),
                        retrieval={"state": "ok", "bytes": info["bytes"], "skipped_existing": info["skipped_existing"]},
                        history=f"downloaded {info['bytes']} bytes sha256={info['sha256'][:12]}")
        gdf = gpd.read_file(raw)
        registry.update(ds_id, status="parsed", parse={"state": "ok", "crs": str(gdf.crs), "features": len(gdf)},
                        history="parsed with geopandas")
        gdf = gdf.set_crs(4326, allow_override=False) if gdf.crs is None else gdf.to_crs(4326)
        gdf, repaired = repair_geometries(gdf)
        rep = validate_vector(gdf, expect_min=expected_n, expect_geom=("Polygon", "MultiPolygon"))
        rep["checks"].append({"check": "geometries_repaired", "passed": True, "detail": str(repaired)})
        ok = rep["passed"] and len(gdf) == expected_n
        if len(gdf) != expected_n:
            rep["checks"].append({"check": "expected_feature_count", "passed": False,
                                  "detail": f"{len(gdf)} != {expected_n}"})
        b = [round(float(x), 5) for x in gdf.total_bounds]
        registry.update(ds_id, status="ready_for_analysis" if ok else "rejected",
                        pune_overlap={"state": "ok" if ok else "failed", "bounds_wgs84": b},
                        quality_checks=rep["checks"], history="validated (CRS->4326, geometry repair, feature count, Pune bbox)")
        if not ok:
            raise ValueError(f"{ds_id} failed validation: {[c for c in rep['checks'] if not c['passed']]}")
        out = data_dir() / "interim" / f"{ds_id}.gpkg"
        out.parent.mkdir(parents=True, exist_ok=True)
        gdf.to_file(out, driver="GPKG")
        outs.append(str(out))
        log.info("%s ready: %d features bounds=%s", ds_id, len(gdf), b)
    return outs
