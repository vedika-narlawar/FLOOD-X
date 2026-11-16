from __future__ import annotations

import json
from datetime import datetime, timezone

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from pipeline import status as pstatus
from pipeline.common import art_dir, data_dir, read_json

from ..repositories import artifacts as repo
from ..schemas.scenario import ScenarioRequest
from ..services import scenario as scen

router = APIRouter(prefix="/api")
PUNE = (73.55, 18.30, 74.15, 18.75)
SEMANTICS = {
    "susceptibility": "Relative physical tendency for flooding from environmental/geographic conditions (screening score, not probability).",
    "hazard": "Flooding characterised by probability/extent/depth for a defined event. NOT produced by this system.",
    "exposure": "People/assets located in an area of interest (here: relatively higher-susceptibility cells). Not flooded, not damaged.",
    "vulnerability": "Propensity of exposed people/assets to harm. NOT assessed.",
    "prediction": "Model-based estimate of future flooding with validation. NOT produced by this system.",
}


def _bbox(bbox: str | None):
    if not bbox:
        return None
    try:
        x0, y0, x1, y1 = (float(v) for v in bbox.split(","))
    except ValueError:
        raise HTTPException(422, "bbox must be 'minLon,minLat,maxLon,maxLat'")
    if not (x0 < x1 and y0 < y1):
        raise HTTPException(422, "bbox min must be less than max")
    if x0 < PUNE[0] - 1 or x1 > PUNE[2] + 1 or y0 < PUNE[1] - 1 or y1 > PUNE[3] + 1:
        raise HTTPException(422, "bbox outside the Pune study region")
    return x0, y0, x1, y1


@router.get("/health")
def health():
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat(timespec="seconds")}


@router.get("/status")
def status():
    led = pstatus.load()["stages"]
    ds = repo.registry_all()
    counts: dict[str, int] = {}
    for d in ds.values():
        counts[d["status"]] = counts.get(d["status"], 0) + 1
    scount: dict[str, int] = {}
    for s in led.values():
        scount[s["status"]] = scount.get(s["status"], 0) + 1
    md = read_json(art_dir() / "models" / "method_decision.json")
    return {"backend": "ok", "datasets_by_status": counts, "stages_by_status": scount,
            "susceptibility_available": repo.layer("susceptibility_grid.geojson").exists(),
            "active_method": md["active_method"] if md else None, "active_path": md["active_path"] if md else None,
            "supervised_model_trained": False,
            "last_pipeline_activity": max((s["finished_at"] for s in led.values()), default=None)}



@router.get("/datasets")
def datasets():
    from pathlib import Path

    root = data_dir()
    local_files = {
        "dem_cop_glo30": [
            root / "raw" / "dem" / "Copernicus_DSM_COG_10_N18_00_E073_00_DEM.tif",
            root / "raw" / "dem" / "Copernicus_DSM_COG_10_N18_00_E074_00_DEM.tif",
        ],
        "landcover_worldcover_2021": [
            root / "raw" / "landcover" / "ESA_WorldCover_10m_2021_v200_N18E072_Map.tif",
        ],
        "population_worldpop_2020": [
            root / "raw" / "population" / "worldpop_ind_2020_pune_clip.tif",
        ],
        "osm_pune": [
            root / "raw" / "osm" / "waterways.json",
            root / "raw" / "osm" / "roads.json",
            root / "raw" / "osm" / "facilities.json",
        ],
    }

    result = []
    for d in repo.registry_all().values():
        item = {
            k: d.get(k) for k in (
                "id", "name", "publisher", "status", "licence",
                "source_url", "last_verified", "blocker", "retrieved_at"
            )
        }

        required = local_files.get(d["id"], [])
        if required:
            existing = [p for p in required if p.is_file()]
            item["local_available"] = len(existing) == len(required)
            item["local_files_found"] = len(existing)
            item["local_files_expected"] = len(required)
        else:
            item["local_available"] = False
            item["local_files_found"] = 0
            item["local_files_expected"] = 0

        item["analysis_ready"] = d["status"] == "ready_for_analysis"
        result.append(item)

    return result



@router.get("/datasets/{dataset_id}")
def dataset(dataset_id: str):
    d = repo.registry_all().get(dataset_id)
    if not d:
        raise HTTPException(404, f"unknown dataset '{dataset_id}'")
    return d


@router.get("/metadata")
def metadata():
    p = data_dir() / "interim" / "study_area.gpkg"
    sa = None
    if p.exists():
        g = repo.read_gdf(p)
        b = g.total_bounds
        sa = {"name": g["name"].iloc[0], "area_km2": round(float(g["area_km2"].iloc[0]), 2), "n_wards": int(g["n_wards"].iloc[0]),
              "analysis_crs": f"EPSG:{int(g['utm_epsg'].iloc[0])}", "bounds_wgs84": [round(float(x), 5) for x in b],
              "source_dataset": "boundaries_pmc_wards_2022 (+ boundaries_pcmc_wards when present)"}
    return {"project": "FLOOD-X", "study_area": sa, "terminology": SEMANTICS,
            "attribution": ["Ward boundaries: DataMeet Trust (CC BY-SA 2.5 IN)", "OSM: (c) OpenStreetMap contributors (ODbL)",
                            "Rainfall: Open-Meteo.com (CC BY 4.0)", "Basemap tiles: (c) OpenStreetMap contributors"]}


@router.get("/study-area")
def study_area():
    p = data_dir() / "interim" / "study_area.gpkg"
    if not p.exists():
        raise repo.Unavailable("study_area", "Study area not built.", ["boundaries", "study_area"])
    return json.loads(repo.read_gdf(p).geometry.simplify(0.0002).to_json())


@router.get("/boundaries/wards")
def wards(simplify: float = Query(0.0001, ge=0, le=0.01)):
    combined = data_dir() / "interim" / "wards_utm.gpkg"
    p = combined if combined.exists() else data_dir() / "interim" / "boundaries_pmc_wards_2022.gpkg"
    if not p.exists():
        raise repo.Unavailable("boundaries", "Ward boundaries not ingested.", ["boundaries"])
    g = repo.read_gdf(p).copy().to_crs(4326)
    g["geometry"] = g.geometry.simplify(simplify, preserve_topology=True)
    if "municipality" not in g.columns:
        g = g.rename(columns={"wardnum": "ward_id", "Name1": "ward_name"})
        g["municipality"] = "PMC"
    g = g[["ward_id", "ward_name", "municipality", "geometry"]]
    fc = json.loads(g.to_json())
    fc["metadata"] = {"source": "boundaries_pmc_wards_2022", "crs": "EPSG:4326", "n_features": len(g),
                      "caveat": "PMC 2022 wards (hand-traced) plus PCMC wards (scraped, vintage undocumented); electoral wards, not drainage units."}
    return fc


@router.get("/features/manifest")
def features_manifest():
    m = repo.feature_manifest()
    if m is None:
        raise repo.Unavailable("features", "Feature manifest not generated.", ["grid_features"])
    return m



@router.get("/rainfall")
def rainfall():
    processed = data_dir() / "processed"
    historical_path = processed / "rainfall_historical.parquet"
    forecast_path = processed / "rainfall_forecast.parquet"

    if not historical_path.exists():
        raise repo.Unavailable(
            "rainfall",
            "Rainfall data not retrieved (Open-Meteo unreachable or stage not run).",
            ["download_rainfall"],
        )

    df = pd.read_parquet(historical_path)
    registry = repo.registry_all()
    d = registry["rainfall_openmeteo_archive"]

    acc = {
        c: (None if df[c].dropna().empty else float(df[c].max()))
        for c in df.columns
        if c.startswith("acc_")
    }

    now = datetime.now(timezone.utc)

    
    def file_metadata(path):
        if not path.exists():
            return {
                "available": False,
                "file_updated_at": None,
                "coverage_start": None,
                "coverage_end": None,
                "rows": 0,
                "missing_hours": None,
                "freshness": "unavailable",
                "age_hours": None,
                "retrieval_age_hours": None,
            }

        stat = path.stat()
        modified = datetime.fromtimestamp(stat.st_mtime, timezone.utc)
        retrieval_age_hours = max(
            0.0, (now - modified).total_seconds() / 3600
        )

        frame = pd.read_parquet(path)

        if frame.empty:
            coverage_start = None
            coverage_end = None
            age_hours = None
            freshness = "unavailable"
        else:
            times = pd.to_datetime(frame["time"])
            coverage_start = str(times.min())
            coverage_end = str(times.max())

            latest = times.max()
            if latest.tzinfo is not None:
                latest = latest.tz_convert("Asia/Kolkata").tz_localize(None)

            current_local = pd.Timestamp.now(
                tz="Asia/Kolkata"
            ).tz_localize(None)

            age_hours = max(
                0.0, (current_local - latest).total_seconds() / 3600
            )

            if path == forecast_path:
                freshness = (
                    "fresh" if latest >= current_local else "outdated"
                )
            elif age_hours <= 24 * 7:
                freshness = "fresh"
            elif age_hours <= 24 * 10:
                freshness = "stale"
            else:
                freshness = "outdated"

        return {
            "available": True,
            "file_updated_at": modified.isoformat(timespec="seconds"),
            "coverage_start": coverage_start,
            "coverage_end": coverage_end,
            "rows": len(frame),
            "missing_hours": (
                int(frame["missing"].sum())
                if "missing" in frame.columns
                else None
            ),
            "freshness": freshness,
            "age_hours": (
                round(age_hours, 1) if age_hours is not None else None
            ),
            "retrieval_age_hours": round(retrieval_age_hours, 1),
        }


    historical = file_metadata(historical_path)
    forecast = file_metadata(forecast_path)

    return {
        "kind": "historical_reanalysis",
        "provider": d["publisher"],
        "units": "mm",
        "timezone": "Asia/Kolkata",
        "retrieved_at": d["retrieved_at"],
        "caveat": "Gridded reanalysis - not a rain-gauge measurement.",
        "rows": len(df),
        "start": str(df["time"].min()),
        "end": str(df["time"].max()),
        "missing_hours": int(df["missing"].sum()),
        "max_trailing_accumulation_mm": acc,
        "forecast_available": forecast["available"],
        "location": d["retrieval"],
        "historical_status": historical,
        "forecast_status": forecast,
        "forecast_issue_time": None,
        "forecast_issue_time_note": (
            "The local file modification time is available, "
            "but the provider's official forecast issue time "
            "is not recorded in this dataset."
        ),
    }



@router.get("/rainfall/series")
def rainfall_series(kind: str = Query("historical", pattern="^(historical|forecast)$"), start: str | None = None,
                    end: str | None = None, agg: str = Query("hourly", pattern="^(hourly|daily)$"),
                    limit: int = Query(5000, ge=1, le=20000)):
    p = data_dir() / "processed" / f"rainfall_{kind}.parquet"
    if not p.exists():
        raise repo.Unavailable("rainfall", f"{kind} rainfall not retrieved.", ["download_rainfall"])
    df = pd.read_parquet(p)
    try:
        if start:
            df = df[df["time"] >= pd.Timestamp(start)]
        if end:
            df = df[df["time"] <= pd.Timestamp(end)]
    except ValueError:
        raise HTTPException(422, "invalid start/end timestamp")
    if agg == "daily":
        s = df.set_index("time")
        df = pd.DataFrame({"precipitation_mm": s["precipitation_mm"].resample("D").sum(min_count=1),
                           "missing": s["missing"].resample("D").sum()}).reset_index()
    df = df.head(limit)
    df["time"] = df["time"].astype(str)
    cols = [c for c in ("time", "precipitation_mm", "missing", "acc_1h_mm", "acc_3h_mm", "acc_6h_mm", "acc_12h_mm", "acc_24h_mm", "acc_72h_mm") if c in df.columns]
    return {"kind": kind, "units": "mm", "agg": agg, "n": len(df), "data": json.loads(df[cols].to_json(orient="records"))}


def _summary(cols: list[str], module: str, label: str):
    m = repo.feature_manifest()
    avail = [c for c in cols if m and m["features"].get(c, {}).get("status") == "available"]
    if not avail:
        reasons = {c: (m or {}).get("features", {}).get(c, {}).get("reason", "feature manifest missing") for c in cols}
        raise repo.Unavailable(module, f"No {label} features available: {reasons}", ["download_dem" if module == "terrain" else "download_landcover", "grid_features"])
    df = repo.read_features()
    return {c: {"units": m["features"][c]["units"], "n_valid": int(df[c].notna().sum()), "mean": float(df[c].mean()),
                "p05": float(df[c].quantile(0.05)), "p50": float(df[c].median()), "p95": float(df[c].quantile(0.95)),
                "source_dataset": m["features"][c]["source_dataset"], "method": m["features"][c]["method"]} for c in avail}


@router.get("/terrain/summary")
def terrain_summary():
    return _summary(["elev_mean_m", "slope_mean_deg", "rel_elev_mean_m"], "terrain", "terrain")


@router.get("/landcover/summary")
def landcover_summary():
    return _summary(["builtup_share", "vegetated_share"], "landcover", "land-cover")


@router.get("/map/raster/{layer}")
def raster_map_layer(layer: str):
    import base64
    import io
    from pathlib import Path

    import numpy as np
    import rasterio
    from PIL import Image
    from rasterio.enums import Resampling
    from rasterio.transform import array_bounds
    from rasterio.warp import calculate_default_transform, reproject

    root = data_dir()

    files = {
        "elevation": root / "processed" / "terrain" / "elevation_utm.tif",
        "slope": root / "processed" / "terrain" / "slope_deg.tif",
        "landcover": root / "raw" / "landcover" / "ESA_WorldCover_10m_2021_v200_N18E072_Map.tif",
        "population": root / "raw" / "population" / "worldpop_ind_2020_pune_clip.tif",
    }

    if layer not in files:
        raise HTTPException(
            status_code=404,
            detail={"reason": "Unknown raster layer", "available": list(files)},
        )

    path = files[layer]
    if not path.is_file():
        raise HTTPException(
            status_code=404,
            detail={"reason": f"Raster file not found: {path.name}"},
        )

    try:
        with rasterio.open(path) as src:
            if src.crs is None:
                raise HTTPException(
                    status_code=422,
                    detail={"reason": "Raster has no coordinate reference system"},
                )

            # Keep the response small enough for browser map overlays.
            scale = min(1.0, 900 / max(src.width, src.height))
            width = max(1, round(src.width * scale))
            height = max(1, round(src.height * scale))

            dst_transform, dst_width, dst_height = calculate_default_transform(
                src.crs,
                "EPSG:4326",
                src.width,
                src.height,
                *src.bounds,
                dst_width=width,
                dst_height=height,
            )

            values = np.full((dst_height, dst_width), np.nan, dtype=np.float32)

            reproject(
                source=rasterio.band(src, 1),
                destination=values,
                src_transform=src.transform,
                src_crs=src.crs,
                src_nodata=src.nodata,
                dst_transform=dst_transform,
                dst_crs="EPSG:4326",
                dst_nodata=np.nan,
                resampling=(
                    Resampling.nearest
                    if layer == "landcover"
                    else Resampling.bilinear
                ),
            )

        valid = np.isfinite(values)
        rgba = np.zeros((values.shape[0], values.shape[1], 4), dtype=np.uint8)

        if not valid.any():
            raise HTTPException(
                status_code=422,
                detail={"reason": "Raster contains no valid pixels"},
            )

        if layer == "landcover":
            # ESA WorldCover class colours.
            palette = {
                10: (0, 100, 0),
                20: (255, 187, 34),
                30: (255, 255, 76),
                40: (240, 150, 255),
                50: (250, 0, 0),
                60: (180, 180, 180),
                70: (240, 240, 240),
                80: (0, 100, 200),
                90: (0, 150, 160),
                95: (0, 207, 117),
                100: (250, 230, 160),
            }
            for code, color in palette.items():
                mask = valid & (np.rint(values) == code)
                rgba[mask, :3] = color
                rgba[mask, 3] = 210

        else:
            low, high = np.percentile(values[valid], [2, 98])
            if high <= low:
                high = low + 1.0
            scaled = np.clip((values - low) / (high - low), 0, 1)
            scaled = np.nan_to_num(scaled)

            if layer == "elevation":
                stops = np.array([
                    [30, 80, 180],
                    [45, 160, 130],
                    [230, 210, 100],
                    [150, 90, 45],
                ], dtype=np.float32)
            elif layer == "slope":
                stops = np.array([
                    [40, 150, 80],
                    [240, 220, 60],
                    [230, 100, 30],
                    [150, 20, 40],
                ], dtype=np.float32)
            else:  # population
                stops = np.array([
                    [255, 245, 180],
                    [255, 160, 60],
                    [210, 30, 30],
                    [100, 0, 30],
                ], dtype=np.float32)

            position = scaled * (len(stops) - 1)
            index = np.minimum(position.astype(np.int32), len(stops) - 2)
            fraction = (position - index)[..., None]
            colors = stops[index] * (1 - fraction) + stops[index + 1] * fraction
            rgba[..., :3] = colors.astype(np.uint8)
            rgba[..., 3] = np.where(valid, 180, 0).astype(np.uint8)

        image = Image.fromarray(rgba, mode="RGBA")
        buffer = io.BytesIO()
        image.save(buffer, format="PNG", optimize=True)

        west, south, east, north = array_bounds(
            rgba.shape[0], rgba.shape[1], dst_transform
        )

        return {
            "layer": layer,
            "image": "data:image/png;base64,"
                     + base64.b64encode(buffer.getvalue()).decode("ascii"),
            "bounds": [[south, west], [north, east]],
            "width": rgba.shape[1],
            "height": rgba.shape[0],
            "crs": "EPSG:4326",
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={"reason": f"Raster rendering failed: {type(exc).__name__}: {exc}"},
        ) from exc


@router.get("/map/osm/{layer}")
def osm_map_layer(
    layer: str,
    bbox: str | None = Query(None, description="minLon,minLat,maxLon,maxLat"),
    limit: int = Query(10000, ge=1, le=50000),
):
    """Return local OSM vector data as map-ready GeoJSON."""
    from pathlib import Path

    files = {
        "waterways": data_dir() / "interim" / "osm_waterways.gpkg",
        "roads": data_dir() / "interim" / "osm_roads.gpkg",
        "facilities": data_dir() / "interim" / "osm_facilities.gpkg",
    }

    if layer not in files:
        raise HTTPException(
            404, "Unknown layer. Choose waterways, roads, or facilities."
        )

    path = files[layer]
    if not path.is_file():
        raise repo.Unavailable(
            f"osm_{layer}", f"Local OSM {layer} file is missing.", ["download_osm"]
        )

    bounds = _bbox(bbox)
    gdf = repo.read_gdf(path).to_crs(4326)

    if bounds:
        from shapely.geometry import box

        area = box(*bounds)
        gdf = gdf[gdf.geometry.intersects(area)]

    total = len(gdf)
    gdf = gdf.head(limit).copy()

    # Remove properties that cannot be safely serialized to GeoJSON.
    for col in gdf.columns:
        if col != gdf.geometry.name:
            gdf[col] = gdf[col].map(
                lambda value: value.item()
                if hasattr(value, "item")
                else value
                if isinstance(value, (str, int, float, bool)) or value is None
                else str(value)
            )

    result = json.loads(gdf.to_json(drop_id=True))
    result["metadata"] = {
        "layer": layer,
        "crs": "EPSG:4326",
        "features_returned": len(gdf),
        "features_matched": total,
        "truncated": total > len(gdf),
        "source": "OpenStreetMap contributors",
        "licence": "ODbL 1.0",
    }
    return result


@router.get("/susceptibility/config")
def susc_config():
    """Index formula, weights and rationale. Always available (static config), independent of data readiness."""
    from pipeline.modeling.index import load_config
    return load_config()


@router.get("/susceptibility/metadata")
def susc_meta():
    p = repo.require_layer("susceptibility_metadata.json", "susceptibility", ["susceptibility_index"],
                           "Screening index has not been computed (required input features unavailable).")
    return json.loads(p.read_text())


@router.get("/susceptibility/zones")
def susc_zones():
    p = repo.require_layer("susceptibility_zones.geojson", "susceptibility", ["susceptibility_index"], "Zonal scores not generated.")
    return json.loads(p.read_text())


@router.get("/susceptibility/grid")
def susc_grid(bbox: str | None = None, category: str | None = None, limit: int = Query(2500, ge=1, le=5000), offset: int = Query(0, ge=0)):
    p = repo.require_layer("susceptibility_grid.geojson", "susceptibility", ["susceptibility_index"], "Susceptibility grid not generated.")
    g = repo.read_gdf(p)
    b = _bbox(bbox)
    if b:
        g = g.cx[b[0]:b[2], b[1]:b[3]]
    if category:
        g = g[g["category"] == category]
    total = len(g)
    fc = json.loads(g.iloc[offset: offset + limit].to_json())
    fc["metadata"] = {"total_matching": total, "offset": offset, "limit": limit, "crs": "EPSG:4326"}
    return fc


@router.get("/exposure/summary")
def exposure_summary():
    p = repo.require_layer("exposure_summary.json", "exposure", ["susceptibility_index", "exposure"],
                           "Exposure not computed: it requires the susceptibility layer plus infrastructure/population inputs.")
    return json.loads(p.read_text())


@router.get("/exposure/facilities")
def exposure_facilities(type: str | None = Query(None, pattern="^(hospital|clinic|school|fire_station|police)$"),
                        bbox: str | None = None, limit: int = Query(1000, ge=1, le=5000)):
    p = repo.require_layer("exposure_facilities.geojson", "exposure", ["download_osm", "exposure"], "OSM facilities not retrieved/joined.")
    g = repo.read_gdf(p)
    if type:
        g = g[g["amenity"] == type]
    b = _bbox(bbox)
    if b:
        g = g.cx[b[0]:b[2], b[1]:b[3]]
    return json.loads(g.head(limit).to_json())


@router.post("/scenarios/evaluate")
def evaluate_scenario(req: ScenarioRequest):
    df = pd.DataFrame(repo.read_features().drop(columns="geometry", errors="ignore"))
    try:
        return scen.evaluate(df, req)
    except ValueError as e:
        raise repo.Unavailable("scenario", f"Scenario cannot be evaluated: {e}", ["grid_features", "susceptibility_index"])


@router.get("/model/metrics")
def model_metrics():
    md = read_json(art_dir() / "models" / "method_decision.json")
    if md is None:
        raise repo.Unavailable("model", "Label audit has not run.", ["label_audit"])
    return {"status": "not_applicable", "supervised_model_trained": False, "active_path": md["active_path"], "reason": md["reason"],
            "metrics": None, "note": "No supervised metrics exist or are reported. Index robustness: see sensitivity.",
            "sensitivity": read_json(art_dir() / "metrics" / "sensitivity.json"), "label_audit": md}


@router.get("/model/explainability")
def model_explain():
    p = repo.require_layer("susceptibility_metadata.json", "explainability", ["susceptibility_index"],
                           "Index not computed, so contribution breakdown is unavailable.")
    meta = json.loads(p.read_text())
    return {"method": meta["method"], "weights": meta["config"]["variables"], "mean_score_contribution": meta["mean_contribution"],
            "note": "Contribution = weight-share x normalised value, averaged over scored cells. Exact decomposition of the additive index."}


@router.get("/pipeline/status")
def pipeline_status():
    led = pstatus.load()
    from pipeline.run import _stages
    order = [n for n, _ in _stages()]
    return {"order": order, "stages": {n: led["stages"].get(n, {"status": "pending", "message": "never run"}) for n in order},
            "history": led["history"][-60:]}


@router.get("/pipeline/probe")
def pipeline_probe():
    p = data_dir() / "registry" / "access_probe.json"
    if not p.exists():
        raise repo.Unavailable("probe", "Access probe has not run.", ["access_probe"])
    return json.loads(p.read_text())
