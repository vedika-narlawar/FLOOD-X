from __future__ import annotations

from .. import registry
from ..common import data_dir, download_file
from ._raster_common import finish_raster_dataset, study_bounds_wgs84

VALID_CODES = {10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 100}


def run(force: bool = False) -> list[str]:
    study_bounds_wgs84()  # raises Blocked early if the study area does not exist
    ds = registry.load()["datasets"]["landcover_worldcover_2021"]
    dest = data_dir() / "raw" / "landcover" / "ESA_WorldCover_10m_2021_v200_N18E072_Map.tif"
    info = download_file(ds["source_url"], dest, min_bytes=5_000_000, force=force)
    finish_raster_dataset("landcover_worldcover_2021", dest, info, value_range=(0, 100), min_valid_fraction=0.9)
    return [str(dest)]
