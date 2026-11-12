"""Tests for erw_siting.protected_areas with synthetic polygons (no network)."""

from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import Polygon, box

from mrv_lab.erw_siting import protected_areas as pa
from mrv_lab.erw_siting.regions import WORK_CRS

# Metric coordinates (EPSG:9377) around Colombia's false origin; 1 unit = 1 m.
X0, Y0 = 5_000_000, 2_000_000
KM = 1_000


@pytest.fixture
def pilot() -> gpd.GeoDataFrame:
    """Two adjacent 10 km x 10 km departments."""
    return gpd.GeoDataFrame(
        {"name": ["Meta", "Tolima"]},
        geometry=[
            box(X0, Y0, X0 + 10 * KM, Y0 + 10 * KM),
            box(X0 + 10 * KM, Y0, X0 + 20 * KM, Y0 + 10 * KM),
        ],
        crs=WORK_CRS,
    )


def _areas(geoms: list[Polygon]) -> gpd.GeoDataFrame:
    n = len(geoms)
    return gpd.GeoDataFrame(
        {
            "name": [f"area {i}" for i in range(n)],
            "category": ["Parque Nacional Natural"] * n,
            "condition": ["REGISTRADA"] * n,
        },
        geometry=geoms,
        crs=WORK_CRS,
    )


def test_read_runap_renames_repairs_and_reprojects(tmp_path: Path) -> None:
    bowtie = Polygon([(-73.0, 4.0), (-72.9, 4.1), (-72.9, 4.0), (-73.0, 4.1)])  # self-intersecting
    raw = gpd.GeoDataFrame(
        {"ap_nombre": ["A"], "ap_categor": ["Reserva Natural"], "condicion": ["INSCRITA"]},
        geometry=[bowtie],
        crs="EPSG:4686",
    )
    path = tmp_path / "runap.gpkg"
    raw.to_file(path, driver="GPKG")

    areas = pa.read_runap(path)

    assert list(areas.columns) == ["name", "category", "condition", "geometry"]
    assert areas.geometry.is_valid.all()
    assert areas.geometry.area.iloc[0] > 0
    assert areas.crs.to_epsg() == 9377


def test_clip_keeps_only_inside_and_tags_department(pilot: gpd.GeoDataFrame) -> None:
    inside_meta = box(X0 + 1 * KM, Y0 + 1 * KM, X0 + 3 * KM, Y0 + 3 * KM)
    across_border = box(X0 + 9 * KM, Y0 + 1 * KM, X0 + 11 * KM, Y0 + 2 * KM)
    outside = box(X0 + 50 * KM, Y0, X0 + 51 * KM, Y0 + 1 * KM)

    clipped = pa.clip_to_pilot(_areas([inside_meta, across_border, outside]), pilot)

    assert sorted(clipped["department"]) == ["Meta", "Meta", "Tolima"]
    assert set(clipped["name"]) == {"area 0", "area 1"}


def test_mask_counts_overlaps_once(pilot: gpd.GeoDataFrame) -> None:
    a = box(X0, Y0, X0 + 2 * KM, Y0 + 2 * KM)  # 400 ha
    b = box(X0 + 1 * KM, Y0, X0 + 3 * KM, Y0 + 2 * KM)  # 400 ha, 200 ha shared with a
    clipped = pa.clip_to_pilot(_areas([a, b]), pilot)

    mask = pa.exclusion_mask(clipped)
    table = pa.summary_table(clipped)

    assert mask.loc[mask["department"] == "Meta", "area_ha"].item() == pytest.approx(600)
    assert table["area_ha"].sum() == pytest.approx(800)  # per-row sums double-count overlaps
    assert table["n_areas"].sum() == 2
