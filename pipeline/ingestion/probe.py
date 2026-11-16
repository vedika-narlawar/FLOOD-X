"""Access probe: records *evidence* of whether each remote source is reachable from the
current environment. Probes never mark a dataset ready; they only record reachability."""
from __future__ import annotations

import socket
from urllib.parse import urlparse

import requests

from .. import registry
from ..common import data_dir, now_iso, user_agent, write_json_atomic

PROBES = {
    "dem_cop_glo30": ("HEAD", "https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N18_00_E073_00_DEM/Copernicus_DSM_COG_10_N18_00_E073_00_DEM.tif"),
    "landcover_worldcover_2021": ("HEAD", "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_N18E072_Map.tif"),
    "population_worldpop_2020": ("HEAD", "https://data.worldpop.org/GIS/Population/Global_2000_2020/2020/IND/ind_ppp_2020.tif"),
    "osm_pune": ("GET", "https://overpass-api.de/api/status"),
    "rainfall_openmeteo_archive": ("GET", "https://archive-api.open-meteo.com/v1/archive?latitude=18.52&longitude=73.86&start_date=2019-08-01&end_date=2019-08-01&hourly=precipitation"),
    "rainfall_openmeteo_forecast": ("GET", "https://api.open-meteo.com/v1/forecast?latitude=18.52&longitude=73.86&hourly=precipitation&forecast_days=1"),
}


def probe_one(method: str, url: str, timeout: float = 15) -> dict:
    host = urlparse(url).hostname
    res = {"url": url, "host": host, "probed_at": now_iso(), "dns_ok": False, "http_status": None,
           "error": None, "deny_reason": None}
    try:
        socket.getaddrinfo(host, 443)
        res["dns_ok"] = True
    except OSError as e:
        res["error"] = f"DNS resolution failed: {e}"
        return res
    try:
        r = requests.request(method, url, timeout=timeout, allow_redirects=True, headers={"User-Agent": user_agent()})
        res["http_status"] = r.status_code
        res["deny_reason"] = r.headers.get("x-deny-reason")
        res["content_length"] = r.headers.get("content-length")
    except requests.RequestException as e:
        res["error"] = f"{type(e).__name__}: {str(e)[:200]}"
    return res


def run() -> list[str]:
    results = {}
    for ds_id, (m, u) in PROBES.items():
        r = probe_one(m, u)
        results[ds_id] = r
        reachable = r["dns_ok"] and r["http_status"] is not None and r["http_status"] < 400
        if reachable:
            registry.update(ds_id, status="access_verified" if registry.load()["datasets"][ds_id]["status"] == "discovered"
                            else registry.load()["datasets"][ds_id]["status"], blocker=None,
                            history=f"access probe OK (HTTP {r['http_status']})")
        else:
            why = r["error"] or f"HTTP {r['http_status']} {r['deny_reason'] or ''}".strip()
            current = registry.load()["datasets"][ds_id]
            registry.update(
                ds_id,
                blocker=f"Remote source not reachable at {r['probed_at']}: {why}",
                history=f"access probe FAILED: {why}; existing processing status preserved ({current['status']})"
            )
    out = data_dir() / "registry" / "access_probe.json"
    write_json_atomic(out, {"probed_at": now_iso(), "results": results})
    return [str(out)]
