"""Tests for erw_siting.weathering (dissolved fraction model, no network)."""

import math

import numpy as np
import pytest

from mrv_lab.erw_siting import weathering as w

BASALT = dict(
    log10_wr_mol_m2_s=-10.53,
    molar_mass_g_per_mol=125.0,
    ea_kj_per_mol=45.2,
    reference_c=25.0,
    ssa_coef=69.18,
    ssa_exponent=-1.24,
)


def test_matches_strefler_equation_at_reference_temperature() -> None:
    # d(x) = SSA(x) * WR * M * t, one year, x = 100 µm
    expected = 69.18 * 100**-1.24 * 10**-10.53 * 125.0 * 3.155e7
    got = w.dissolved_fraction(p80_um=100, years=1, temperature_c=25.0, **BASALT)
    assert float(got) == pytest.approx(expected)


def test_capped_at_one_and_finer_dissolves_more() -> None:
    fractions = [
        float(w.dissolved_fraction(p80_um=p, years=10, temperature_c=25.0, **BASALT))
        for p in (1000, 100, 10)
    ]
    assert fractions[0] < fractions[1] < fractions[2] == 1.0


def test_arrhenius_colder_is_slower() -> None:
    assert w.arrhenius_factor(25.0, 45.2, 25.0) == pytest.approx(1.0)
    cold = w.arrhenius_factor(np.array([15.0, 20.0]), 45.2, 25.0)
    expected_15 = math.exp(-45.2e3 / w.GAS_CONSTANT_J_PER_MOL_K * (1 / 288.15 - 1 / 298.15))
    assert cold[0] == pytest.approx(expected_15) and cold[0] < cold[1] < 1.0


def test_registry_values_ranges_contain_values() -> None:
    for pid, v in w.registry_values().items():
        if v["range"] is not None:
            assert v["range"][0] <= v["value"] <= v["range"][1], pid


def test_serpentinization_slows_the_ultramafic_rate() -> None:
    import pandas as pd

    s = w.serpentinized_fraction(pd.Series([0.0, 6.25, 12.5, 14.0]))
    assert s.tolist() == [0.0, 0.5, 1.0, 1.0]  # capped at fully serpentinized
    fresh = w.effective_log10_wr(-9.86, 0.0, -1.76)
    assert fresh == pytest.approx(-9.86)
    mixed = w.effective_log10_wr(-9.86, 0.7, -1.76)
    expected = -9.86 + math.log10(0.3 + 0.7 * 10**-1.76)
    assert mixed == pytest.approx(expected) and -10.4 < mixed < -10.3


def test_serpentine_ratio_from_palandri_kharaka() -> None:
    v = w.registry_values()["log10_rate_ratio_serpentine_forsterite"]
    assert v["value"] == pytest.approx(-12.40 + 10.64)
    assert v["range"] == [pytest.approx(-1.76), pytest.approx(-1.36)]
