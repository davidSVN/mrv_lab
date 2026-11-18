"""Tests for F7 second round: scenario table, recent temperature, history (no network)."""

from pathlib import Path

import geopandas as gpd
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import box

from mrv_lab.erw_siting import climate, history
from mrv_lab.erw_siting import sensitivity as s


def test_scenarios_are_complete_and_consistent() -> None:
    assert len(s.SCENARIOS) == 8
    for name, grain, _overrides, _settings, route, temperature in s.SCENARIOS.values():
        assert grain in ("coarse", "medium", "fine") and name
        assert route in ("apta", "apta_mixta", s.META_MAIN_ROUTE, s.NO_ULTRAMAFIC_ROUTE)
        assert temperature in ("t2m_mean_c", s.RECENT_T2M)
    assert s.SCENARIOS["s7_fine_rinder_grinding"][2] == {"grinding_kwh_per_t_fine": 173.0}


def _tif(path: Path, data: np.ndarray) -> Path:
    profile = {
        "driver": "GTiff",
        "dtype": "float32",
        "count": data.shape[0],
        "height": data.shape[1],
        "width": data.shape[2],
        "crs": "EPSG:4326",
        "transform": from_origin(-74.0, 4.4, 0.1, 0.1),
        "nodata": np.nan,
    }
    with rasterio.open(path, "w", **profile) as out:
        out.write(data.astype("float32"))
    return path


def test_recent_temperature_uses_1996_2025(tmp_path: Path) -> None:
    # months 1991-1995 at 0 °C, 1996-2020 at 20 °C, 2021-2025 at 26 °C -> mean (25*20 + 5*26)/30
    base = np.full((360, 4, 4), 20 + 273.15)
    base[:60] = 273.15
    extra = np.full((60, 4, 4), 26 + 273.15)
    pilot = gpd.GeoDataFrame({"name": ["Meta"]}, geometry=[box(-74.0, 4.0, -73.6, 4.4)], crs=4326)
    out = climate.recent_temperature(
        pilot, _tif(tmp_path / "b.tif", base), _tif(tmp_path / "e.tif", extra), tmp_path
    )
    with rasterio.open(out["Meta"]) as src:
        values = src.read(1)
    assert np.nanmean(values) == pytest.approx((25 * 20 + 5 * 26) / 30, abs=0.01)


def test_history_snapshot_copies_into_version_folder(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(history, "history_dir", lambda: tmp_path / "history")
    f = tmp_path / "summary.csv"
    f.write_text("a,b\n1,2\n")
    folder = history.snapshot([f], tag="2026-11-18_abc1234")
    assert (folder / "summary.csv").read_text() == "a,b\n1,2\n"
    assert history.version_tag()[:4].isdigit()
