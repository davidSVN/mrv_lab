"""Tests for erw_siting.quarries with synthetic roads and rock (no network)."""

import geopandas as gpd
import pytest
from shapely.geometry import LineString, MultiLineString, box

from mrv_lab.erw_siting import quarries as q
from mrv_lab.erw_siting.regions import WORK_CRS

X0, Y0, KM = 5_000_000, 2_000_000, 1_000


def test_sample_points_spacing() -> None:
    line = LineString([(0, 0), (20 * KM, 0)])
    pts = q.sample_points(line, 5 * KM)
    assert [p.x for p in pts] == [2.5 * KM, 7.5 * KM, 12.5 * KM, 17.5 * KM]
    short = q.sample_points(MultiLineString([[(0, 0), (1 * KM, 0)]]), 5 * KM)
    assert len(short) == 1  # a short stretch still gets one point


@pytest.fixture
def rock() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        {"unit_code": [1, 2], "final_class": ["Apta", "Mixta"], "ultramafic": [False, True]},
        geometry=[
            box(X0, Y0, X0 + 2 * KM, Y0 + 2 * KM),
            box(X0 + 50 * KM, Y0, X0 + 52 * KM, Y0 + 2 * KM),
        ],
        crs=WORK_CRS,
    )


def test_potential_sources_access_distance_and_classes(rock: gpd.GeoDataFrame) -> None:
    roads = gpd.GeoDataFrame(
        {"highway": ["primary", "tertiary", "secondary"]},
        geometry=[
            LineString([(X0 - 10 * KM, Y0 + 1 * KM), (X0 + 10 * KM, Y0 + 1 * KM)]),  # crosses Apta
            LineString(
                [(X0 + 45 * KM, Y0 + 4 * KM), (X0 + 57 * KM, Y0 + 4 * KM)]
            ),  # 2 km from Mixta
            LineString([(X0, Y0 + 40 * KM), (X0 + 10 * KM, Y0 + 40 * KM)]),  # far from any rock
        ],
        crs=WORK_CRS,
    )
    sources = q.potential_sources(roads, rock, max_access_km=5, spacing_km=5)

    assert set(sources["final_class"]) == {"Apta", "Mixta"}
    assert (sources["access_km"] <= 5).all()
    assert sources.loc[sources["final_class"] == "Mixta", "ultramafic"].eq(1).all()
    apta = sources[sources["final_class"] == "Apta"]
    assert apta["access_km"].min() == 0  # dense sampling finds the road on the rock
    assert len(apta) <= 4  # 12 km of road -> at most one point per 5 x 5 km square
    assert sources["rock_source_id"].is_unique
    assert (sources["origin"] == "potential").all()


def test_thin_to_grid_keeps_closest_per_square() -> None:
    pts = gpd.GeoDataFrame(
        {"final_class": ["Apta"] * 3, "access_m": [900.0, 100.0, 50.0]},
        geometry=gpd.points_from_xy([X0 + 100, X0 + 4_000, X0 + 6_000], [Y0, Y0, Y0]),
        crs=WORK_CRS,
    )
    thin = q.thin_to_grid(pts, spacing_km=5)
    assert sorted(thin["access_m"]) == [50.0, 100.0]  # one per 5 km square, closest kept
