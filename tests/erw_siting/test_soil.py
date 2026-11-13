"""Tests for erw_siting.soil with synthetic rasters (no network)."""

import geopandas as gpd
import numpy as np
import pytest
from rasterio.crs import CRS
from rasterio.transform import from_origin
from shapely.geometry import box

from mrv_lab.erw_siting import soil

NODATA = -32768


def test_layer_url() -> None:
    assert soil.layer_url("phh2o", "0-5cm", "Q0.05") == (
        "https://files.isric.org/soilgrids/latest/data/phh2o/phh2o_0-5cm_Q0.05.vrt"
    )


def test_depth_weighted_uses_thickness_and_propagates_nodata() -> None:
    top = np.array([[50, 50]], dtype="int16")  # 0-5 cm
    mid = np.array([[60, NODATA]], dtype="int16")  # 5-15 cm
    low = np.array([[70, 70]], dtype="int16")  # 15-30 cm

    out = soil.depth_weighted([top, mid, low], [5, 10, 15], NODATA)

    assert out[0, 0] == pytest.approx((50 * 5 + 60 * 10 + 70 * 15) / 30)
    assert np.isnan(out[0, 1])


def test_conversion_factors_match_isric_table() -> None:
    assert 55 / soil.VARIABLES["phh2o"][1] == pytest.approx(5.5)
    assert 1350 / soil.VARIABLES["bdod"][1] == pytest.approx(13.5)  # cg/cm3 -> kg/dm3 /100
    assert soil.VARIABLES["cec"][2] == "cmol(c)/kg"


def test_to_work_grid_reprojects_and_masks_outside() -> None:
    # 0.1 deg x 0.1 deg raster of constant 5.0 around (-73.5, 4.0), WGS84.
    data = np.full((40, 40), 5.0, dtype="float32")
    transform = from_origin(-73.6, 4.1, 0.005, 0.005)
    outline = gpd.GeoSeries([box(-73.55, 3.95, -73.45, 4.05)], crs="EPSG:4326")

    grid, _ = soil.to_work_grid(data, transform, CRS.from_epsg(4326), outline)

    inside = grid[~np.isnan(grid)]
    assert inside.size > 0
    assert np.allclose(inside, 5.0, atol=1e-4)
    assert np.isnan(grid).sum() > 0  # pixels outside the outline are masked


def test_with_retries_recovers_then_gives_up() -> None:
    calls: list[int] = []
    waits: list[float] = []

    def flaky() -> str:
        calls.append(1)
        if len(calls) < 3:
            raise soil.rasterio.errors.RasterioIOError("reset")
        return "ok"

    assert soil.with_retries(flaky, delays_s=(1, 2, 3), sleep=waits.append) == "ok"
    assert waits == [1, 2]

    def always_fails() -> str:
        raise soil.rasterio.errors.RasterioIOError("reset")

    with pytest.raises(soil.rasterio.errors.RasterioIOError):
        soil.with_retries(always_fails, delays_s=(1,), sleep=waits.append)
