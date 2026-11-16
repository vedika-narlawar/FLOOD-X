import pandas as pd
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
