"""Pipeline orchestrator. `python -m pipeline.run [--stage NAME ...] [--force]`.
Every stage records an honest status in artifacts/pipeline_status.json."""
from __future__ import annotations

import argparse
import sys
import traceback

from . import registry, status
from .common import Blocked, SourceUnavailable, get_logger, now_iso

log = get_logger("floodx.run")


def _stages():
    from .exposure import analysis as exposure
    from .features import build
    from .inference import susceptibility
    from .ingestion import boundaries, dem, landcover, osm, population, probe, rainfall
    from .modeling import label_audit
    from .preprocessing import grid, study_area
    return [
        ("registry_init", lambda force: [str(registry.path())] if registry.load() else []),
        ("access_probe", lambda force: probe.run()),
        ("boundaries", lambda force: boundaries.run(force)),
        ("study_area", lambda force: study_area.run()),
        ("grid", lambda force: grid.run()),
        ("label_audit", lambda force: label_audit.run()),
        ("download_dem", lambda force: dem.run(force)),
        ("download_landcover", lambda force: landcover.run(force)),
        ("download_population", lambda force: population.run(force)),
        ("download_osm", lambda force: osm.run(force)),
        ("download_rainfall", lambda force: rainfall.run()),
        ("terrain", lambda force: build.terrain_stage()),
        ("grid_features", lambda force: build.run()),
        ("susceptibility_index", lambda force: susceptibility.run()),
        ("exposure", lambda force: exposure.run()),
    ]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", action="append", help="run only these stages")
    ap.add_argument("--force", action="store_true", help="re-download raw files")
    a = ap.parse_args(argv)
    registry.load()
    failures = 0
    for name, fn in _stages():
        if a.stage and name not in a.stage:
            continue
        t0 = now_iso()
        log.info("== stage %s", name)
        try:
            outs = fn(a.force)
            status.record(name, "success", "completed", outs, t0)
        except Blocked as e:
            status.record(name, "blocked", e.reason, [], t0, {"missing": e.missing})
            log.warning("BLOCKED %s: %s", name, e.reason)
        except SourceUnavailable as e:
            status.record(name, "blocked", f"Remote source unavailable: {e}", [], t0, {"kind": "network"})
            log.warning("BLOCKED(network) %s: %s", name, e)
        except Exception as e:
            failures += 1
            status.record(name, "failed", f"{type(e).__name__}: {e}", [], t0, {"traceback": traceback.format_exc()[-1500:]})
            log.error("FAILED %s: %s", name, e)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
