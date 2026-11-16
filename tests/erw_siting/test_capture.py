"""Tests for erw_siting.capture (charge-based capture potential, no network)."""

import pytest

from mrv_lab.erw_siting import capture as c


def test_one_mole_of_calcium_stores_two_eta() -> None:
    # Renforth & Henderson 2017: eta 0.831 -> 1.66 mol CO2 per mol Ca2+.
    # 100 g of pure CaO = 100/56.077 mol Ca; t CO2 per t rock = mol * 2 eta * M_CO2 / 100
    r = c.capture_potential_t_co2_per_t({"CaO": 100.0}, c.ETA)
    mol_ca = 100 / c.OXIDE_MOLAR_MASS["CaO"]
    assert r == pytest.approx(mol_ca * 2 * 0.831 * c.CO2_MOLAR_MASS / 100)
    eta_per_divalent = 2 * c.ETA
    assert eta_per_divalent == pytest.approx(1.66, abs=0.005)


def test_alkali_oxides_count_two_charges() -> None:
    # Na2O releases 2 Na+ = 2 moles of charge per mole of oxide, same as CaO (not 0.5 omega).
    per_mol_na2o = c.capture_potential_t_co2_per_t({"Na2O": c.OXIDE_MOLAR_MASS["Na2O"]}, 1.0)
    per_mol_cao = c.capture_potential_t_co2_per_t({"CaO": c.OXIDE_MOLAR_MASS["CaO"]}, 1.0)
    assert per_mol_na2o == pytest.approx(per_mol_cao)


def test_registry_ranges_contain_values() -> None:
    for pid, v in c.registry_values().items():
        assert v["range"][0] <= v["value"] <= v["range"][1], pid
