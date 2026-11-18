"""Tests for erw_siting.monte_carlo (draws, simulation, summary, tornado; no network)."""

import numpy as np
import pandas as pd
import pytest

from mrv_lab.erw_siting import monte_carlo as mc
from mrv_lab.erw_siting import net_removal as nr
from mrv_lab.erw_siting import registry


@pytest.fixture(scope="module")
def table() -> pd.DataFrame:
    return registry.load()


@pytest.fixture(scope="module")
def base_values(table: pd.DataFrame) -> dict[str, float]:
    ok = table[table["status"] == "ok"]
    return {r["id"]: float(r["value"]) for r in ok.to_dict("records")}


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "cell_id": ["a", "b", "c"],
            "department": ["Meta", "Meta", "Valle del Cauca"],
            "candidate": [1, 1, 0],
            "excluded_by": [None, None, "slope"],
            "rock_class": ["basalt", "ultramafic", None],
            "arc_volcanic": [False, False, False],
            "rock_source_id": ["R1", "R2", None],
            "road_km": [50.0, 300.0, 10.0],
            "t2m_mean_c": [26.0, 20.0, 24.0],
            "phh2o": [5.0, 6.2, 6.0],
            "dry_months": [0.0, 1.0, 0.0],
        }
    )


def _samples() -> dict[str, pd.DataFrame]:
    basalt = pd.DataFrame(
        {"CaO": [10.0, 12.0], "MgO": [8.0, 9.0], "Na2O": [2.0, 3.0], "K2O": [0.1, 0.2]}
    )
    ultra = pd.DataFrame(
        {"CaO": [0.5, 1.0], "MgO": [40.0, 42.0], "Na2O": [np.nan, 0.1], "K2O": [0.0, 0.01]}
    )
    return {"basalt": basalt, "ultramafic": ultra}


def test_uncertain_parameters_exclude_definitions_oxides_and_choices(table: pd.DataFrame) -> None:
    ids = set(mc.uncertain_parameters(table)["id"])
    assert "log10_wr_basalt_mol_m2_s" in ids and "grid_ef_kgco2_per_kwh" in ids
    assert not ids & {"horizon_years", "application_rate_t_per_ha", "acid_soil_ph_threshold"}
    assert not any("_wt_pct_" in i for i in ids)


def test_draws_stay_in_range_and_are_reproducible(table: pd.DataFrame) -> None:
    a = mc.draw_parameters(table, 200, np.random.default_rng(1))
    b = mc.draw_parameters(table, 200, np.random.default_rng(1))
    pd.testing.assert_frame_equal(a, b)
    ranges = mc.uncertain_parameters(table).set_index("id")
    for pid in a.columns:
        assert a[pid].between(ranges.loc[pid, "low"], ranges.loc[pid, "high"]).all()


def test_rock_draws_keep_samples_whole() -> None:
    rock = mc.draw_rock(_samples(), 50, np.random.default_rng(2))
    pairs = set(zip(rock["cao_wt_pct_basalt"], rock["mgo_wt_pct_basalt"], strict=True))
    assert pairs <= {(10.0, 8.0), (12.0, 9.0)}
    assert (rock["cao_wt_pct_gabbro"] == rock["cao_wt_pct_basalt"]).all()  # gabbro = basalt proxy
    assert rock["na2o_wt_pct_ultramafic"].notna().all()  # blank -> set median


def test_simulation_at_base_values_equals_f6(base_values: dict[str, float]) -> None:
    frame = _frame()
    params = pd.DataFrame({"grid_ef_kgco2_per_kwh": [base_values["grid_ef_kgco2_per_kwh"]] * 3})
    oxides = {k: [v] * 3 for k, v in base_values.items() if "_wt_pct_" in k}
    ids, net = mc.simulate(frame, base_values, params, pd.DataFrame(oxides), "medium")
    f6 = nr.compute(frame, base_values, "medium").set_index("cell_id")
    assert list(ids) == ["a", "b"]
    np.testing.assert_allclose(net[:, 0], f6.loc[["a", "b"], "net_tco2_per_t"], rtol=1e-5)


def test_summary_quantiles_and_probability() -> None:
    net = np.array([[-1.0, 1.0, 2.0, 3.0], [-1.0, -2.0, -3.0, -4.0]], dtype="float32")
    s = mc.summarise(net, rate_t_per_ha=20, horizon_years=10)
    assert s["p_net_positive"].tolist() == [0.75, 0.0]
    assert s.loc[0, "net_ha_p50_tco2_per_ha_yr"] == pytest.approx(np.median(net[0]) * 2)


def test_tornado_faster_weathering_raises_net(
    table: pd.DataFrame, base_values: dict[str, float]
) -> None:
    t = mc.tornado(_frame(), base_values, table)
    row = t[(t["department"] == "Meta") & (t["parameter"] == "log10_wr_basalt_mol_m2_s")].iloc[0]
    assert row["at_high"] > row["at_low"]
    assert not t["parameter"].isin(["horizon_years", "grinding_kwh_per_t_fine"]).any()
