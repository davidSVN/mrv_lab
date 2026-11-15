"""Tests for erw_siting.grid (synthetic geometries, no network)."""

import geopandas as gpd
import numpy as np
import pytest
from shapely.geometry import box

from mrv_lab.erw_siting import grid as g
from mrv_lab.erw_siting.regions import WORK_CRS

X0, Y0 = 5_000_000, 2_000_000


def test_grid_aligned_to_kilometres_and_ids() -> None:
    grid = g.Grid((X0 + 250, Y0 + 100, X0 + 2_900, Y0 + 1_800))
    assert grid.x0 == X0 and grid.y1 == Y0 + 2_000
    assert grid.shape == (2, 3)
    assert grid.cell_ids(np.array([1]), np.array([0])) == [f"E{X0 // 1000}_N{Y0 // 1000}"]


def test_polygon_fraction_half_cell() -> None:
    grid = g.Grid((X0, Y0, X0 + 2_000, Y0 + 1_000))
    frac = g.polygon_fraction(grid, [box(X0, Y0, X0 + 500, Y0 + 1_000)])
    assert frac[0, 0] == pytest.approx(0.5)
    assert frac[0, 1] == pytest.approx(0.0)


def test_build_cells_assigns_border_cell_by_area() -> None:
    pilot = gpd.GeoDataFrame(
        {"name": ["A", "B"]},
        geometry=[box(X0, Y0, X0 + 1_300, Y0 + 1_000), box(X0 + 1_300, Y0, X0 + 3_000, Y0 + 1_000)],
        crs=WORK_CRS,
    )
    _, cells, _, _ = g.build_cells(pilot)
    assert len(cells) == 3
    middle = cells.sort_values("x_center_m").iloc[1]
    assert middle["department"] == "B"  # 70 % of the middle cell is in B
    assert middle["area_in_department_km2"] == pytest.approx(0.7)
