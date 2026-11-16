"""Tests for erw_siting.soil_losses (two-class soil loss, no network)."""

import numpy as np
import pytest

from mrv_lab.erw_siting import soil_losses as s


def test_two_classes_by_ph_and_nan_kept() -> None:
    got = s.loss_fraction(np.array([4.8, 5.5, 6.9, np.nan]), 5.5, 0.68, 0.33)
    assert got[:3].tolist() == [0.68, 0.33, 0.33]  # threshold itself is not acidic
    assert np.isnan(got[3])


def test_values_follow_the_source_numbers() -> None:
    v = s.registry_values()
    assert v["f_loss_acid_soil"]["value"] == pytest.approx(1 - 1 / 3.1, abs=0.005)
    assert v["f_loss_acid_soil"]["range"][0] == pytest.approx(1 - 1.30 / 2, abs=0.005)
    assert v["f_loss_neutral_soil"]["value"] == pytest.approx(1 - 1 / 1.5, abs=0.005)
    assert v["acid_soil_ph_threshold"]["value"] == 5.5
    assert v["f_loss_neutral_soil"]["value"] < v["f_loss_acid_soil"]["value"]
