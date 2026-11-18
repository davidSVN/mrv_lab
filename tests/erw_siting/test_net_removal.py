"""Tests for erw_siting.net_removal (F6 chain on synthetic cells, registry values, no network)."""

import numpy as np
import pandas as pd
import pytest

from mrv_lab.erw_siting import capture, registry
from mrv_lab.erw_siting import net_removal as nr


@pytest.fixture(scope="module")
def values() -> dict[str, float]:
    table = registry.load()
    ok = table[table["status"] == "ok"]
    return {r["id"]: float(r["value"]) for r in ok.to_dict("records")}


def test_candidates_report_every_failed_rule() -> None:
    filters = pd.DataFrame(
        {
            "cell_id": ["a", "b"],
            "protected_frac": [0.0, 0.9],
            "frontier_unconditioned_frac": [1.0, 0.1],
            "agro_use_frac": [0.8, 0.8],
            "slope_gt12_frac": [0.1, 0.7],
        }
    )
    got = nr.candidates(filters)
    assert got["candidate"].tolist() == [1, 0]
    assert got.loc[1, "excluded_by"] == "protected;frontier;slope"
    assert pd.isna(got.loc[0, "excluded_by"])


def test_rock_class_rules() -> None:
    units = pd.DataFrame(
        {
            "unit_code": [1, 2, 3, 4],
            "rock_types": ["basalt; dolerite", "gabbro; norite", "harzburgite; gabbro", "gabbro"],
            "ultramafic": [0, 0, 1, 0],
        }
    )
    assert nr.rock_class(units).tolist() == ["basalt", "gabbro", "ultramafic", "gabbro"]


def _frame(**overrides) -> pd.DataFrame:  # noqa: ANN003
    base = {
        "cell_id": ["c"],
        "candidate": [1],
        "excluded_by": [None],
        "rock_class": ["basalt"],
        "arc_volcanic": [False],
        "rock_source_id": ["RS1"],
        "road_km": [100.0],
        "t2m_mean_c": [25.0],
        "phh2o": [6.5],
        "dry_months": [0.0],
    }
    return pd.DataFrame({**base, **{k: [v] for k, v in overrides.items()}})


def test_chain_matches_hand_calculation(values: dict[str, float]) -> None:
    out = nr.compute(_frame(), values, "medium").iloc[0]
    v = values
    r = capture.capture_potential_t_co2_per_t(
        {ox: v[f"{ox.lower()}_wt_pct_basalt"] for ox in nr.OXIDES}, v["eta_mol_co2_per_mol_charge"]
    )
    per_year = (
        v["ssa_coef_m2_per_g"]
        * 100 ** v["ssa_exponent"]
        * 10 ** v["log10_wr_basalt_mol_m2_s"]
        * v["molar_mass_basalt_g_per_mol"]
        * 3.155e7
    )
    f_diss = min(1.0, per_year * v["horizon_years"])  # 25 °C = reference: Arrhenius factor 1
    gross = r * f_diss * (1 - v["f_loss_neutral_soil"])
    diesel = v["diesel_ef_kgco2_per_l"] / 1000
    per_km = v["truck_l_diesel_per_t_km"] * v["empty_return_factor"] * diesel
    grind = v["grinding_kwh_per_t_medium"] * v["grid_ef_kgco2_per_kwh"] / 1000
    spread = v["spreading_l_diesel_per_t"] * diesel
    net = gross - grind - 100 * per_km - spread
    assert out["cdr_gross_tco2_per_t"] == pytest.approx(gross)
    assert out["net_tco2_per_t"] == pytest.approx(net)
    assert out["breakeven_km"] == pytest.approx((gross - grind - spread) / per_km)
    assert out["margin_km"] == pytest.approx(out["breakeven_km"] - 100)
    assert out["net_ha_tco2_per_ha_yr"] == pytest.approx(net * 20 / 10)
    assert out["lime_demand"] == 0


def test_acid_cold_far_is_worse_and_noncandidates_stay_empty(values: dict[str, float]) -> None:
    good = nr.compute(_frame(), values, "medium").iloc[0]
    bad = nr.compute(_frame(phh2o=4.8, t2m_mean_c=18.0, road_km=400.0), values, "medium").iloc[0]
    assert bad["net_tco2_per_t"] < good["net_tco2_per_t"] and bad["lime_demand"] == 1
    skipped = nr.compute(_frame(candidate=0, excluded_by="slope"), values, "medium").iloc[0]
    assert np.isnan(skipped["net_tco2_per_t"]) and skipped["data_quality"] is None


def test_coarse_grain_is_net_negative_even_next_to_the_quarry(values: dict[str, float]) -> None:
    out = nr.compute(_frame(road_km=0.0), values, "coarse").iloc[0]
    assert out["net_tco2_per_t"] < 0


def test_flags(values: dict[str, float]) -> None:
    out = nr.compute(
        _frame(rock_class="gabbro", arc_volcanic=True, dry_months=2.0), values, "medium"
    ).iloc[0]
    assert out["data_quality"] == "gabbro_proxy;arc_volcanic_source;dry_months:2"
