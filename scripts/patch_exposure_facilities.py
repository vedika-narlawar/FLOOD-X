"""Fix: exposure summary treated every 'n_*' column (incl. n_inputs_used) as a facility count.
Idempotent; backs up changed files; writes tests/unit/test_exposure.py."""
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "pipeline" / "exposure" / "analysis.py"
TEST = ROOT / "tests" / "unit" / "test_exposure.py"
if not SRC.exists():
    sys.exit(f"STOP: {SRC} not found. Run from your flood-x folder.")

raw = SRC.read_bytes().decode("utf-8")
crlf = "\r\n" in raw
t = raw.replace("\r\n", "\n")


def once(text, old, new, label):
    if text.count(old) != 1:
        sys.exit(f"STOP: anchor '{label}' found {text.count(old)} times (expected 1). Nothing changed. Send me this message.")
    return text.replace(old, new)


changed = False
if "FACILITY_COLS" not in t:
    t = once(t, 'CATS = ["Very low", "Low", "Moderate", "High", "Very high"]',
             'CATS = ["Very low", "Low", "Moderate", "High", "Very high"]\n'
             '# Only these columns are facility counts. Other n_* columns (e.g. n_inputs_used) are NOT facilities.\n'
             'FACILITY_COLS = ("n_hospital", "n_clinic", "n_school", "n_fire_station", "n_police")', "constant")
    t = once(t, 'cols = [c for c in g.columns if c.startswith("n_")]',
             'cols = [c for c in FACILITY_COLS if c in g.columns and g[c].notna().any()]', "column selection")
    t = once(t, '"reason": "OSM facility counts not in feature grid"',
             '"reason": "OSM facility counts are not available in the feature grid"', "reason text")
    changed = True

TEST_SRC = '''import pandas as pd
import pytest

from pipeline.exposure.analysis import CATS, FACILITY_COLS, summarise

NO_FAC_REASON = "OSM facility counts are not available in the feature grid"


def grid(**cols):
    n = 5
    d = {"score": [10.0, 30, 50, 70, 90], "category": CATS, "n_inputs_used": [4] * n}
    d.update(cols)
    return pd.DataFrame(d)


def test_n_inputs_used_alone_is_not_a_facility():
    """The bug: n_inputs_used (variables per cell) was reported as a facility count."""
    s = summarise(grid(), None)["sections"]["facilities"]
    assert s["status"] == "unavailable" and s["reason"] == NO_FAC_REASON
    assert "by_category" not in s


def test_real_facility_columns_counted_and_n_inputs_used_excluded():
    g = grid(n_hospital=[0, 1, 0, 2, 0], n_school=[1, 1, 1, 1, 1])
    s = summarise(g, None)["sections"]["facilities"]
    assert s["status"] == "available"
    for cat_counts in s["by_category"].values():
        assert set(cat_counts) <= set(FACILITY_COLS) and "n_inputs_used" not in cat_counts
    assert sum(v["n_hospital"] for v in s["by_category"].values()) == 3
    assert sum(v["n_school"] for v in s["by_category"].values()) == 5
    assert s["by_category"]["High"]["n_hospital"] == 2


def test_all_missing_facility_column_is_unusable():
    g = grid(n_hospital=[float("nan")] * 5)
    assert summarise(g, None)["sections"]["facilities"]["status"] == "unavailable"


def test_mixed_usable_and_unusable_facility_columns():
    g = grid(n_hospital=[float("nan")] * 5, n_police=[0, 0, 1, 0, 0])
    by = summarise(g, None)["sections"]["facilities"]["by_category"]
    assert all(set(v) == {"n_police"} for v in by.values()) and by["Moderate"]["n_police"] == 1


def test_zero_counts_are_usable_when_layer_exists():
    g = grid(n_clinic=[0.0] * 5)
    s = summarise(g, None)["sections"]["facilities"]
    assert s["status"] == "available" and sum(v["n_clinic"] for v in s["by_category"].values()) == 0


def test_roads_and_population_behaviour_unchanged():
    secs = summarise(grid(road_length_m=[1000.0] * 5, population_sum=[10.0, 20, 30, 40, 50]), None)["sections"]
    assert secs["roads"]["status"] == "available" and secs["roads"]["by_category"]["Low"] == 1.0
    assert secs["population"]["total"] == pytest.approx(150.0) and secs["population"]["by_category"]["Very high"] == 50.0
    none = summarise(grid(), None)["sections"]
    assert none["roads"]["status"] == "unavailable" and none["population"]["status"] == "unavailable"
'''

stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
bdir = ROOT / "backups" / f"exposure-fix-{stamp}"
if changed:
    (bdir / "pipeline" / "exposure").mkdir(parents=True, exist_ok=True)
    shutil.copy2(SRC, bdir / "pipeline" / "exposure" / "analysis.py")
    SRC.write_bytes((t.replace("\n", "\r\n") if crlf else t).encode("utf-8"))
if TEST.exists() and changed:
    shutil.copy2(TEST, bdir / "test_exposure.py")
TEST.parent.mkdir(parents=True, exist_ok=True)
TEST.write_text(TEST_SRC, encoding="utf-8")
print("Patched analysis.py" if changed else "analysis.py already patched", "| test file:", TEST.relative_to(ROOT), "| backups:", bdir if changed else "none")