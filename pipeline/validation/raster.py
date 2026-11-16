
"""Raster validation: readability, CRS, resolution, NoData, overlap with study area."""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import geometry_mask
from rasterio.warp import transform_bounds, transform_geom


def validate_raster(
    path: Path,
    study_bounds_wgs84: tuple[float, float, float, float],
    *,
    min_valid_fraction: float = 0.5,
    value_range: tuple[float, float] | None = None,
    sample_max: int = 2_000_000,
) -> dict:
    checks, ok = [], True

    def add(name, passed, detail=""):
        nonlocal ok
        ok &= bool(passed)
        checks.append({
            "check": name,
            "passed": bool(passed),
            "detail": str(detail),
        })

    info: dict = {}
    try:
        with rasterio.open(path) as ds:
            add("readable", True)
            info = {
                "crs": str(ds.crs),
                "width": ds.width,
                "height": ds.height,
                "count": ds.count,
                "dtype": ds.dtypes[0],
                "nodata": ds.nodata,
                "res": [abs(ds.res[0]), abs(ds.res[1])],
                "bounds": list(ds.bounds),
                "units": ds.units[0] if ds.units else None,
            }

            add("has_crs", ds.crs is not None, ds.crs)

            if ds.crs is not None:
                b = transform_bounds(ds.crs, "EPSG:4326", *ds.bounds)
                sb = study_bounds_wgs84
                overlaps = (
                    b[0] < sb[2] and b[2] > sb[0]
                    and b[1] < sb[3] and b[3] > sb[1]
                )
                add(
                    "covers_study_area",
                    overlaps,
                    f"raster {np.round(b, 4).tolist()} "
                    f"vs study {np.round(sb, 4).tolist()}",
                )

            # Read the actual study-area polygon.
            study_path = path.parents[1] / "interim" / "study_area.gpkg"
            if not study_path.exists():
                # Use the project's configured data directory.
                from ..common import data_dir
                study_path = data_dir() / "interim" / "study_area.gpkg"

            if study_path.exists() and ds.crs is not None:
                study = gpd.read_file(study_path).to_crs(ds.crs)
                geometries = [
                    geom.__geo_interface__
                    for geom in study.geometry
                    if geom is not None and not geom.is_empty
                ]

                if geometries:
                    # Restrict the sample to the study polygon's raster window.
                    from rasterio.windows import from_bounds, Window

                    bounds = study.total_bounds
                    window = from_bounds(*bounds, transform=ds.transform)
                    window = window.round_offsets().round_lengths()

                    col0 = max(0, int(window.col_off))
                    row0 = max(0, int(window.row_off))
                    col1 = min(ds.width, col0 + int(window.width))
                    row1 = min(ds.height, row0 + int(window.height))

                    if col1 > col0 and row1 > row0:
                        win = Window(col0, row0, col1 - col0, row1 - row0)
                        factor = max(
                            1,
                            int(np.ceil(np.sqrt(win.width * win.height / sample_max))),
                        )
                        out_h = max(1, int(np.ceil(win.height / factor)))
                        out_w = max(1, int(np.ceil(win.width / factor)))
                        arr = ds.read(
                            1,
                            window=win,
                            out_shape=(out_h, out_w),
                            masked=True,
                        )

                        # Rasterize the polygon at the same sampled resolution.
                        from affine import Affine
                        sample_transform = ds.window_transform(win) * Affine.scale(
                            win.width / out_w,
                            win.height / out_h,
                        )
                        inside = geometry_mask(
                            geometries,
                            out_shape=arr.shape,
                            transform=sample_transform,
                            invert=True,
                            all_touched=False,
                        )
                        denominator = int(inside.sum())
                        valid_count = int((inside & ~np.ma.getmaskarray(arr)).sum())
                        valid = valid_count / denominator if denominator else 0.0

                        info["valid_fraction_sampled"] = round(valid, 4)
                        info["valid_pixels_sampled_in_study_area"] = valid_count
                        info["study_area_pixels_sampled"] = denominator
                        add(
                            "sufficient_valid_pixels",
                            denominator > 0 and valid >= min_valid_fraction,
                            f"{valid:.3f} valid within study area "
                            f"({valid_count}/{denominator} sampled pixels)",
                        )

                        vals = arr.data[inside & ~np.ma.getmaskarray(arr)]
                        if vals.size:
                            info["min"] = float(vals.min())
                            info["max"] = float(vals.max())
                            if value_range:
                                add(
                                    "values_in_range",
                                    value_range[0] <= info["min"] <= info["max"]
                                    <= value_range[1],
                                    f"[{info['min']}, {info['max']}] "
                                    f"vs {value_range}",
                                )
                    else:
                        add("sufficient_valid_pixels", False, "Study area does not overlap raster")
                else:
                    add("sufficient_valid_pixels", False, "Study area has no usable geometry")
            else:
                add(
                    "sufficient_valid_pixels",
                    False,
                    "Study-area geometry unavailable or raster CRS missing",
                )

    except Exception as e:
        add("readable", False, f"{type(e).__name__}: {e}")

    return {"passed": ok, "checks": checks, "info": info}
