"""Tests for erw_siting.climate (no network)."""

import numpy as np
import pytest

from mrv_lab.erw_siting import climate


def test_rainfall_indicators_sum_and_dry_months() -> None:
    monthly = np.full((12, 1, 2), 100.0)
    monthly[:3, 0, 1] = 20.0  # three dry months in the second pixel
    out = climate.rainfall_indicators(monthly)
    assert out["rain_annual_mm"][0, 0] == pytest.approx(1200.0)
    assert out["rain_annual_mm"][0, 1] == pytest.approx(9 * 100 + 3 * 20)
    assert out["dry_months"][0].tolist() == [0.0, 3.0]


def test_era5_request_area_is_north_west_south_east() -> None:
    req = climate.era5_request((-77.0, 2.0, -71.0, 5.5))
    assert req["area"] == [5.5, -77.0, 2.0, -71.0]
    assert len(req["year"]) == 30
    assert req["product_type"] == ["monthly_averaged_reanalysis"]


def test_days_in_months_counts_leap_years() -> None:
    days = climate.days_in_months((2019, 2020))
    assert days.shape == (24,)
    assert days.sum() == 365 + 366


def test_era5_indicators_units_and_sign() -> None:
    n = len(climate.YEARS) * 12
    t2m = np.full((n, 1, 1), 300.15)  # 27 °C
    pev = np.full((n, 1, 1), -0.004)  # -4 mm/day (evaporation is negative in ECMWF)
    e = np.full((n, 1, 1), -0.003)
    out = climate.era5_indicators(t2m, pev, e)
    days_per_year = climate.days_in_months().sum() / len(climate.YEARS)
    assert out["t2m_mean_c"][0, 0] == pytest.approx(27.0)
    assert out["pet_annual_mm"][0, 0] == pytest.approx(4.0 * days_per_year)
    assert out["et_annual_mm"][0, 0] == pytest.approx(3.0 * days_per_year)
