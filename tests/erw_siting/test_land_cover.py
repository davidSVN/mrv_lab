"""Tests for erw_siting.land_cover with synthetic class rasters (no network)."""

import geopandas as gpd
import numpy as np
import pytest
from rasterio.crs import CRS
from rasterio.transform import from_origin
from shapely.geometry import box

from mrv_lab.erw_siting import land_cover as lc


def test_agro_classes_follow_decision() -> None:
    assert lc.AGRO_CLASSES == (21, 35, 74)
    assert 9 not in lc.AGRO_CLASSES  # forest plantation excluded
    assert lc.CLASSES[21] == "Mosaic of agriculture and pasture"


def test_reprojection_keeps_only_original_classes_and_masks_outside() -> None:
    # Two halves: class 21 (west) and class 3 (east), 0.1 deg square in WGS84.
    data = np.full((300, 300), 3, dtype="uint8")
    data[:, :150] = 21
    transform = from_origin(-73.6, 4.1, 0.1 / 300, 0.1 / 300)
    outline = gpd.GeoSeries([box(-73.58, 4.02, -73.52, 4.08)], crs="EPSG:4326")

    grid, _ = lc.to_work_grid(data, transform, CRS.from_epsg(4326), outline)

    assert set(np.unique(grid)) <= {lc.NODATA, 3, 21}  # nearest: no averaged codes
    assert (grid == lc.NODATA).any()


def test_class_areas_hectares_and_flags() -> None:
    grid = np.array([[21, 21, 3], [lc.NODATA, 35, 9]], dtype="uint8")

    table = lc.class_areas(grid, pixel_area_m2=900.0).set_index("class_id")

    assert table.loc[21, "area_ha"] == pytest.approx(2 * 0.09)
    assert bool(table.loc[35, "agricultural_use"]) is True
    assert bool(table.loc[9, "agricultural_use"]) is False
    assert lc.NODATA not in table.index
