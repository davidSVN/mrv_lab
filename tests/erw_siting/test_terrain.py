"""Tests for erw_siting.terrain (no network)."""

import numpy as np
import pytest

from mrv_lab.erw_siting import terrain


def test_tile_name_uses_south_west_corner() -> None:
    assert terrain.tile_name(4, -74) == "Copernicus_DSM_COG_10_N04_00_W074_00_DEM"
    assert terrain.tile_name(-1, 10) == "Copernicus_DSM_COG_10_S01_00_E010_00_DEM"


def test_tiles_for_bounds_covers_every_degree_cell() -> None:
    names = terrain.tiles_for_bounds((-74.5, 3.2, -73.1, 4.8))
    assert len(names) == 4  # 2 lon x 2 lat cells
    assert "Copernicus_DSM_COG_10_N03_00_W075_00_DEM" in names
    assert "Copernicus_DSM_COG_10_N04_00_W074_00_DEM" in names


def test_slope_of_known_plane() -> None:
    # Rises 3 m every 30 m pixel in x -> 10 % slope everywhere.
    x = np.arange(20) * 3.0
    plane = np.tile(x, (20, 1))
    slope = terrain.slope_percent(plane, pixel_m=30.0)
    assert np.allclose(slope, 10.0)


def test_band_shares_sum_to_one_and_ignore_nan() -> None:
    slope = np.array([[1.0, 5.0, 9.0, 20.0], [np.nan, 3.0, 11.0, 30.0]], dtype="float32")
    shares = terrain.band_shares(slope)
    assert shares["0-8%"] + shares["8-12%"] + shares["12-inf%"] == pytest.approx(1.0)
    assert shares["0-8%"] == pytest.approx(3 / 7)
