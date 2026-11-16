"""WorldPop. The national raster is large; we try an HTTP range (windowed) read of the Pune
window first, which avoids a full-country download, and write the clip as the raw artefact."""
from __future__ import annotations

import rasterio
from rasterio.windows import from_bounds

from .. import registry
from ..common import SourceUnavailable, data_dir, now_iso, sha256_file
from ._raster_common import finish_raster_dataset, study_bounds_wgs84


def run(force: bool = False) -> list[str]:
    study_bounds_wgs84()
    ds = registry.load()["datasets"]["population_worldpop_2020"]
    dest = data_dir() / "raw" / "population" / "worldpop_ind_2020_pune_clip.tif"
    if dest.exists() and not force:
        info = {"sha256": sha256_file(dest), "retrieved_at": None, "bytes": dest.stat().st_size}
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        w, s, e, n = study_bounds_wgs84()
        pad = 0.01
        try:
            with rasterio.Env(GDAL_HTTP_TIMEOUT="60", GDAL_HTTP_MAX_RETRY="4", GDAL_HTTP_RETRY_DELAY="2"):
                with rasterio.open(ds["source_url"]) as src:
                    win = from_bounds(w - pad, s - pad, e + pad, n + pad, src.transform).round_offsets().round_lengths()
                    data = src.read(1, window=win)
                    prof = src.profile | {"height": data.shape[0], "width": data.shape[1],
                                          "transform": src.window_transform(win), "driver": "GTiff", "compress": "deflate"}
                    nodata, units = src.nodata, src.units
        except rasterio.errors.RasterioIOError as e:
            raise SourceUnavailable(f"WorldPop read failed: {e}") from e
        tmp = dest.with_suffix(".tif.part")
        with rasterio.open(tmp, "w", **prof) as out:
            out.write(data, 1)
            out.update_tags(source=ds["source_url"], retrieved_at=now_iso(), note="values: people per pixel (verify)")
        tmp.replace(dest)
        info = {"sha256": sha256_file(dest), "retrieved_at": now_iso(), "bytes": dest.stat().st_size}
    # population counts must be non-negative
    finish_raster_dataset("population_worldpop_2020", dest, info, value_range=(0, 1e6), min_valid_fraction=0.5)
    return [str(dest)]
