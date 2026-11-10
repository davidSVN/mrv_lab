"""Tests for erw_siting.regions with synthetic squares (no network)."""

import geopandas as gpd
import pytest
from shapely.geometry import box

from mrv_lab.erw_siting import regions


@pytest.fixture
def departments() -> gpd.GeoDataFrame:
    """Four fake departments in WGS84, names spelled with odd case and accents."""
    return gpd.GeoDataFrame(
        {"name": ["META", "Tólima", "Valle Del  Cauca", "Huila"]},
        geometry=[
            box(-73, 3, -72, 4),
            box(-75, 4, -74, 5),
            box(-77, 3, -76, 4),
            box(-76, 2, -75, 3),
        ],
        crs="EPSG:4326",
    ).to_crs(regions.WORK_CRS)


def test_normalize_name() -> None:
    assert regions.normalize_name("Valle Del  Cáuca") == "valle del cauca"


def test_selects_pilot_ignoring_case_and_accents(departments: gpd.GeoDataFrame) -> None:
    pilot = regions.select_pilot_departments(departments)
    assert list(pilot["name"]) == ["Meta", "Tolima", "Valle del Cauca"]


def test_missing_department_raises_with_available_names(departments: gpd.GeoDataFrame) -> None:
    with pytest.raises(KeyError, match="Available: .*Huila"):
        regions.select_pilot_departments(departments, names=("Meta", "Atlántico"))


def test_output_crs_is_work_crs(departments: gpd.GeoDataFrame) -> None:
    pilot = regions.select_pilot_departments(departments)
    assert pilot.crs.to_epsg() == 9377
    assert all(a > 0 for a in regions.area_km2(pilot))
