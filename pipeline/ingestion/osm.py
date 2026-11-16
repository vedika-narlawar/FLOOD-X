"""OpenStreetMap via Overpass (`out geom` JSON) -> GeoPackage layers. Respects Overpass policy:
single sequential queries, identifying User-Agent, bounded retries."""
from __future__ import annotations

import json
import time

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, Point, Polygon

from .. import registry
from ..common import data_dir, get_logger, now_iso, request_with_retry, sha256_file
from ._raster_common import study_bounds_wgs84

log = get_logger("floodx.osm")
URL = "https://overpass-api.de/api/interpreter"

QUERIES = {
    "waterways": '[out:json][timeout:180];(way["waterway"~"^(river|stream|canal|drain)$"]({bb}););out geom tags;',
    "roads": '[out:json][timeout:180];(way["highway"~"^(motorway|trunk|primary|secondary|tertiary|unclassified|residential|motorway_link|trunk_link|primary_link|secondary_link)$"]({bb}););out geom tags;',
    "facilities": '[out:json][timeout:180];(nwr["amenity"~"^(hospital|clinic|school|fire_station|police)$"]({bb}););out center geom tags;',
}


def overpass_to_gdf(payload: dict) -> gpd.GeoDataFrame:
    """Parse Overpass `out geom` JSON. Closed ways with area-type tags -> centroid points for facilities."""
    rows = []
    for el in payload.get("elements", []):
        tags = el.get("tags", {})
        geom = None
        if el["type"] == "node" and "lon" in el:
            geom = Point(el["lon"], el["lat"])
        elif el["type"] == "way" and el.get("geometry"):
            pts = [(p["lon"], p["lat"]) for p in el["geometry"]]
            if len(pts) >= 2:
                geom = LineString(pts)
        elif el.get("center"):
            geom = Point(el["center"]["lon"], el["center"]["lat"])
        if geom is None:
            continue
        rows.append({"osm_type": el["type"], "osm_id": el["id"], "geometry": geom, "tags_json": json.dumps(tags, ensure_ascii=False),
                     "amenity": tags.get("amenity"), "highway": tags.get("highway"), "waterway": tags.get("waterway"),
                     "name": tags.get("name")})
    gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs=4326) if rows else gpd.GeoDataFrame(
        {"osm_type": [], "osm_id": [], "geometry": []}, geometry="geometry", crs=4326)
    return gdf.drop_duplicates(subset=["osm_type", "osm_id"]) if len(gdf) else gdf


def facilities_to_points(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Facilities mapped as areas come back with `center`; lines are reduced to representative points."""
    g = gdf.copy()
    g["geometry"] = g.geometry.apply(lambda x: x if x.geom_type == "Point" else x.representative_point())
    return g


def run(force: bool = False) -> list[str]:
    w, s, e, n = study_bounds_wgs84()
    bb = f"{s - 0.005},{w - 0.005},{n + 0.005},{e + 0.005}"
    outs, counts = [], {}
    for name, q in QUERIES.items():
        dest = data_dir() / "raw" / "osm" / f"{name}.json"
        if not dest.exists() or force:
            r = request_with_retry("POST", URL, data={"data": q.format(bb=bb)}, timeout=240, retries=3, backoff=5)
            if r.status_code != 200:
                from ..common import SourceUnavailable
                raise SourceUnavailable(f"Overpass HTTP {r.status_code}: {r.text[:200]}")
            payload = r.json()  # raises on malformed
            if "elements" not in payload:
                from ..common import SourceUnavailable
                raise SourceUnavailable("Overpass returned no 'elements' key (likely a runtime error remark)")
            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp = dest.with_suffix(".json.part")
            tmp.write_text(json.dumps(payload))
            tmp.replace(dest)
            time.sleep(5)  # be polite between sequential queries
        gdf = overpass_to_gdf(json.loads(dest.read_text()))
        if name == "facilities":
            gdf = facilities_to_points(gdf)
        out = data_dir() / "interim" / f"osm_{name}.gpkg"
        gdf.to_file(out, driver="GPKG")
        counts[name] = len(gdf)
        outs.append(str(out))
    registry.update("osm_pune", status="quality_checked" if all(counts.values()) else "parsed",
                    retrieval={"state": "ok", "retrieved_at": now_iso()}, retrieved_at=now_iso(),
                    parse={"state": "ok", "feature_counts": counts},
                    quality_checks=[{"check": f"{k}_nonempty", "passed": v > 0, "detail": str(v)} for k, v in counts.items()],
                    history="Overpass queries executed; counts are NOT a completeness claim")
    return outs
