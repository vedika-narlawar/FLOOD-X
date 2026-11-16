"""Generates docs/dataset_audit.md and docs/data_quality_report.md from the registry + probe evidence."""
import sys; sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
import json
from pathlib import Path

from pipeline import registry, status
from pipeline.common import data_dir, now_iso, read_json

ROOT = Path(__file__).resolve().parents[1]
reg = registry.load()["datasets"]
probe = (read_json(data_dir() / "registry" / "access_probe.json") or {}).get("results", {})
led = status.load()["stages"]

L = [f"# Dataset Audit\n\n_Generated {now_iso()} by `scripts/gen_audit.py` from `data/registry/datasets.json`. Nothing here is hand-edited; statuses reflect executed checks only._\n",
     "| ID | Status | Licence | Pune overlap | Last verified |", "|---|---|---|---|---|"]
for d in reg.values():
    L.append(f"| `{d['id']}` | **{d['status']}** | {d['licence']} | {d['pune_overlap'].get('state')} | {d['last_verified'] or '—'} |")
L.append("")
for d in reg.values():
    L += [f"\n## {d['name']} (`{d['id']}`)", f"- Publisher: {d['publisher']}", f"- Source: {d['source_url']}", f"- Attribution: {d['attribution']}",
          f"- Version/date range: {d['version']} / {d['date_range']}", f"- Coverage: {d['geographic_coverage']}",
          f"- Resolution: {d['spatial_resolution']} spatial, {d['temporal_resolution']} temporal", f"- Format/units: {d['format']} / {d['units']}",
          f"- Download method: {d['download_method']}", f"- **Status: {d['status']}**", f"- Retrieval: `{json.dumps(d['retrieval'])}`",
          f"- Parse: `{json.dumps(d['parse'])[:300]}`", f"- Intended use: {d['intended_use']}", "- Known limitations:"]
    L += [f"  - {x}" for x in d["known_limitations"]]
    if d["blocker"]:
        L.append(f"- **Blocker:** {d['blocker']}")
    p = probe.get(d["id"])
    if p:
        L.append(f"- Access probe ({p['probed_at']}): dns_ok={p['dns_ok']}, http={p['http_status']}, error={p['error']}")
    if d["quality_checks"]:
        L.append("- Quality checks:")
        L += [f"  - {'PASS' if c['passed'] else 'FAIL'} `{c['check']}` — {c['detail']}" for c in d["quality_checks"]]
L.append("\n## Flood-label research note\nOne web search was executed (not exhaustive). Pune's 25 Sept 2019 flood is documented in news reporting (Down To Earth via PreventionWeb) but no georeferenced, downloadable, provenance-documented observation set was found. SAR flood-mapping studies surfaced were for Kerala, Malda and Bangladesh and were rejected as non-Pune. The Chennai-specific material mentioned in the brief was not used.")
(ROOT / "docs" / "dataset_audit.md").write_text("\n".join(L) + "\n")

Q = [f"# Data Quality Report\n\n_Generated {now_iso()}._\n", "## Pipeline stage outcomes\n", "| Stage | Status | Message |", "|---|---|---|"]
for k, v in led.items():
    Q.append(f"| `{k}` | {v['status']} | {str(v['message'])[:200].replace('|', '/')} |")
Q.append("\n## Executed validation (boundaries)\n")
for i in ("boundaries_pmc_wards_2022", "boundaries_pmc_admin_wards_2017"):
    d = reg[i]
    Q.append(f"**{i}** — sha256 `{(d['sha256'] or '')[:16]}…`, bounds {d['pune_overlap'].get('bounds_wgs84')}")
    Q += [f"- {'PASS' if c['passed'] else 'FAIL'} {c['check']}: {c['detail']}" for c in d["quality_checks"]]
Q.append("\nAll raster/OSM/rainfall validators are implemented and unit-tested on synthetic fixtures, but have **not** been run on real provider data in this environment (network blocked).")
(ROOT / "docs" / "data_quality_report.md").write_text("\n".join(Q) + "\n")
print("docs written")
