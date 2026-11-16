"""Open-Meteo hourly precipitation (historical reanalysis and forecast kept in separate files)."""
from __future__ import annotations
from datetime import date, timedelta

import pandas as pd

from .. import registry
from ..common import SourceUnavailable, data_dir, now_iso, request_with_retry

ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
FORECAST = "https://api.open-meteo.com/v1/forecast"
WINDOWS_H = (1, 3, 6, 12, 24, 72)


def parse_openmeteo(payload: dict, *, product: str, kind: str, retrieved_at: str) -> pd.DataFrame:
    if "hourly" not in payload or "time" not in payload["hourly"] or "precipitation" not in payload["hourly"]:
        raise SourceUnavailable(f"Open-Meteo response lacks hourly precipitation: {str(payload)[:200]}")
    h = payload["hourly"]
    df = pd.DataFrame({"time": pd.to_datetime(h["time"]), "precipitation_mm": h["precipitation"]})
    df["precipitation_mm"] = pd.to_numeric(df["precipitation_mm"], errors="coerce")
    df["missing"] = df["precipitation_mm"].isna()
    if (df["precipitation_mm"] < 0).any():
        raise ValueError("negative precipitation values in provider response")
    df.attrs.update(latitude=payload.get("latitude"), longitude=payload.get("longitude"),
                    timezone=payload.get("timezone"), units=payload.get("hourly_units", {}).get("precipitation"),
                    product=product, kind=kind, retrieved_at=retrieved_at)
    return df


def rolling_accumulations(df: pd.DataFrame, windows=WINDOWS_H) -> pd.DataFrame:
    """Trailing sums only (uses current and *past* hours). Windows with any missing hour -> NaN."""
    s = df.set_index("time")["precipitation_mm"].asfreq("h")
    out = pd.DataFrame(index=s.index)
    for w in windows:
        out[f"acc_{w}h_mm"] = s.rolling(w, min_periods=w).sum()
    return out.reset_index()


def _fetch(url, params, label):
    r = request_with_retry("GET", url, params=params, timeout=60)
    if r.status_code != 200:
        raise SourceUnavailable(f"{label} HTTP {r.status_code}: {r.text[:200]}")
    return r.json()


def run(start=None, end=None, centroid=None, **_) -> list[str]:
    if end is None:
        end = (date.today() - timedelta(days=5)).isoformat()
    if start is None:
        start = (date.fromisoformat(end) - timedelta(days=29)).isoformat()
    import geopandas as gpd
    from ..common import Blocked
    if not (data_dir() / "interim" / "study_area.gpkg").exists():
        raise Blocked("study_area.gpkg missing; run the 'study_area' stage first", ["study_area"])
    c = gpd.read_file(data_dir() / "interim" / "study_area.gpkg").to_crs(4326).geometry.union_all().centroid
    lat, lon = (centroid or (round(c.y, 3), round(c.x, 3)))
    outs = []
    ts = now_iso()
    base = {"latitude": lat, "longitude": lon, "hourly": "precipitation", "timezone": "Asia/Kolkata"}
    hist = parse_openmeteo(_fetch(ARCHIVE, {**base, "start_date": start, "end_date": end}, "archive"),
                           product="Open-Meteo historical (reanalysis)", kind="historical_reanalysis", retrieved_at=ts)
    p = data_dir() / "processed" / "rainfall_historical.parquet"
    p.parent.mkdir(parents=True, exist_ok=True)
    pd.concat([hist, rolling_accumulations(hist).drop(columns="time")], axis=1).to_parquet(p)
    outs.append(str(p))
    registry.update("rainfall_openmeteo_archive", status="quality_checked", retrieved_at=ts,
                    retrieval={"state": "ok", "start": start, "end": end, "lat": lat, "lon": lon},
                    parse={"state": "ok", "rows": len(hist), "missing_rows": int(hist["missing"].sum()),
                           "units": hist.attrs["units"], "timezone": hist.attrs["timezone"]},
                    history="hourly precipitation retrieved; rolling trailing accumulations computed")
    fc = parse_openmeteo(_fetch(FORECAST, {**base, "forecast_days": 7}, "forecast"),
                         product="Open-Meteo forecast", kind="forecast", retrieved_at=ts)
    p2 = data_dir() / "processed" / "rainfall_forecast.parquet"
    fc.to_parquet(p2)
    outs.append(str(p2))
    registry.update("rainfall_openmeteo_forecast", status="quality_checked", retrieved_at=ts,
                    retrieval={"state": "ok"}, parse={"state": "ok", "rows": len(fc), "units": fc.attrs["units"]},
                    history="forecast retrieved (kept separate from historical)")
    return outs
