"""Tests for erw_siting.agricultural_frontier with fake pages (no network)."""

from pathlib import Path
from urllib.parse import parse_qs, urlparse

import geopandas as gpd
import pytest
from shapely.geometry import box

from mrv_lab import io
from mrv_lab.erw_siting import agricultural_frontier as af


def _write_page(path: Path, ids: list[int], frontier_type: str = "No condicionada") -> None:
    """Fake GeoJSON page: one 0.01 deg square per id, in WGS84 like the real service."""
    gdf = gpd.GeoDataFrame(
        {
            "objectid": ids,
            "departamen": ["Meta"] * len(ids),
            "cod_dane_mpio": ["50006"] * len(ids),
            "municipio": ["Acacías"] * len(ids),
            "tipo_frontera": [frontier_type] * len(ids),
        },
        geometry=[box(-73.5 + i * 0.02, 4.0, -73.49 + i * 0.02, 4.01) for i in ids],
        crs="EPSG:4326",
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(path, driver="GeoJSON")


def test_page_url_filters_department_and_pages() -> None:
    query = parse_qs(urlparse(af.page_url("50", 4000)).query)
    assert query["where"] == ["cod_depart='50'"]
    assert query["resultOffset"] == ["4000"]
    assert query["orderByFields"] == ["objectid"]
    assert query["f"] == ["geojson"]


def test_fetch_stops_after_short_page(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Page size 2: pages of 2, 2, 1 features -> exactly three requests."""
    pages = {0: [1, 2], 2: [3, 4], 4: [5]}
    requested: list[int] = []

    def fake_download(url: str, dest: Path, **_: object) -> Path:
        offset = int(parse_qs(urlparse(url).query)["resultOffset"][0])
        requested.append(offset)
        _write_page(dest, pages[offset])
        return dest

    monkeypatch.setattr(io, "download_file", fake_download)
    paths = af.fetch_frontier({"Meta": "50"}, page_size=2, raw_dir=tmp_path)

    assert requested == [0, 2, 4]
    assert len(paths) == 3


def test_read_drops_duplicates_and_reprojects(tmp_path: Path) -> None:
    _write_page(tmp_path / "a.geojson", [1, 2])
    _write_page(tmp_path / "b.geojson", [2, 3])  # objectid 2 repeated across pages

    frontier = af.read_frontier([tmp_path / "a.geojson", tmp_path / "b.geojson"])

    assert sorted(frontier["objectid"]) == [1, 2, 3]
    assert frontier.crs.to_epsg() == 9377
    assert set(frontier.columns) >= {"department", "municipality", "frontier_type"}


def test_mask_area_by_type(tmp_path: Path) -> None:
    _write_page(tmp_path / "a.geojson", [1, 2], "No condicionada")
    _write_page(tmp_path / "b.geojson", [3], "Condicionada")
    frontier = af.read_frontier([tmp_path / "a.geojson", tmp_path / "b.geojson"])

    mask = af.frontier_mask(frontier).set_index("frontier_type")

    assert mask.loc["No condicionada", "n_polygons"] == 2
    assert mask.loc["Condicionada", "n_polygons"] == 1
    square_ha = frontier.geometry.area.iloc[0] / 10_000
    assert mask.loc["No condicionada", "area_ha"] == pytest.approx(2 * square_ha, rel=1e-3)
