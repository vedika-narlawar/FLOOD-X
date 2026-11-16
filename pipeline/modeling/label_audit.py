"""Decides the analytical path from the *actual* label inventory. A label set is accepted only if
a provenance sidecar (<name>.provenance.json) documents event, date, method and licence, and
it contains enough georeferenced positive observations. Nothing is ever fabricated."""
from __future__ import annotations

import json

from ..common import art_dir, data_dir, now_iso, write_json_atomic

MIN_POSITIVES = 100  # minimum georeferenced flood observations for spatial-CV supervised modelling
REQUIRED_PROVENANCE = ("event", "observation_date", "method", "licence", "source_url", "crs", "label_type")


def audit() -> dict:
    d = data_dir() / "raw" / "flood_labels"
    candidates = []
    if d.exists():
        for prov in sorted(d.glob("*.provenance.json")):
            meta = json.loads(prov.read_text())
            missing = [k for k in REQUIRED_PROVENANCE if k not in meta]
            candidates.append({"file": prov.name, "missing_provenance": missing,
                               "n_positive": meta.get("n_positive"), "label_type": meta.get("label_type")})
    credible = [c for c in candidates if not c["missing_provenance"] and (c["n_positive"] or 0) >= MIN_POSITIVES
                and c["label_type"] == "verified_flood_observation"]
    if credible:
        path, reason = "A", f"{len(credible)} credible label set(s) with >= {MIN_POSITIVES} verified positives found (supervised pipeline not yet implemented in this build)"
    else:
        path = "B"
        reason = ("No credible, georeferenced, downloadable flood-observation dataset with documented provenance is present in data/raw/flood_labels/. "
                  "Supervised training would require inventing labels, which is prohibited. The explainable screening index is therefore active.")
    res = {"audited_at": now_iso(), "active_path": path, "reason": reason, "candidates_inspected": candidates,
           "min_positives_required": MIN_POSITIVES, "required_provenance_fields": list(REQUIRED_PROVENANCE),
           "active_method": "GIS-Based Flood Susceptibility Screening Index" if path == "B" else "supervised (pending)",
           "supervised_model_trained": False}
    write_json_atomic(art_dir() / "models" / "method_decision.json", res)
    return res


def run() -> list[str]:
    audit()
    return [str(art_dir() / "models" / "method_decision.json")]
