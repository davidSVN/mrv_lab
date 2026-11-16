"""Tests for erw_siting.emission_factors (formulas and source checks, no network)."""

import math

import pytest

from mrv_lab.erw_siting import emission_factors as ef

GRAINS = {"coarse": 1000.0, "medium": 100.0, "fine": 10.0}


def test_bond_law_matches_hand_calculation() -> None:
    # W = 10 * Wi * (1/sqrt(P80) - 1/sqrt(F80)), sizes in µm
    expected = 10 * 20.41 * (1 / math.sqrt(100) - 1 / math.sqrt(5000))
    assert ef.bond_kwh_per_t(20.41, 100, 5000) == pytest.approx(expected)
    assert ef.bond_kwh_per_t(20.41, 5000, 5000) == 0.0


def test_finer_grain_costs_more_energy() -> None:
    values = ef.registry_values(GRAINS)
    coarse, medium, fine = (values[f"grinding_kwh_per_t_{g}"]["value"] for g in GRAINS)
    assert coarse < medium < fine
    assert coarse > ef.CRUSHING_KWH_PER_T  # crushing to 5 mm always included


def test_derived_values() -> None:
    values = ef.registry_values(GRAINS)
    assert values["diesel_ef_kgco2_per_l"]["value"] == pytest.approx(10.180 / 3.785411784, abs=1e-3)
    assert values["empty_return_factor"]["value"] == pytest.approx(1 + 6.48 / 15.55, abs=0.01)
    truck = values["truck_l_diesel_per_t_km"]
    assert truck["range"][0] <= truck["value"] <= truck["range"][1]
    assert values["grid_ef_kgco2_per_kwh"]["value"] == ef.GRID_INVENTORY_T_PER_MWH[2024]


def test_verify_reports_missing_patterns() -> None:
    texts = {key: "" for key in ef.SOURCES}
    problems = ef.verify(texts)
    n_checks = sum(len(s["checks"]) for s in ef.SOURCES.values())
    assert len(problems) == n_checks
    texts["upme_085_2026"] = "B. Factor de emisión para inventarios de GEI:\n   0.220 tonCO2eq/MWh"
    assert len(ef.verify(texts)) == n_checks - 1
