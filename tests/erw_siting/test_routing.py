"""Tests for erw_siting.routing on a tiny synthetic network (no network access)."""

import geopandas as gpd
import numpy as np
import pytest
from shapely.geometry import LineString, Point

from mrv_lab.erw_siting import routing as r
from mrv_lab.erw_siting.regions import WORK_CRS


@pytest.fixture
def graph() -> r.RoadGraph:
    # An L-shaped road: (0,0) -> (10000,0) -> (10000,10000), plus a separate road far away.
    lines = gpd.GeoSeries(
        [
            LineString([(0, 0), (10_000, 0)]),
            LineString([(10_000, 0), (10_000, 10_000)]),
            LineString([(90_000, 90_000), (91_000, 90_000)]),
        ],
        crs=WORK_CRS,
    )
    return r.RoadGraph(lines)


def test_road_distance_follows_the_road(graph: r.RoadGraph) -> None:
    sources = gpd.GeoDataFrame(
        {"rock_source_id": ["RS1"], "final_class": ["Apta"], "access_km": [0.5]},
        geometry=[Point(0, 0)],
        crs=WORK_CRS,
    )
    cells = gpd.GeoDataFrame(
        {
            "cell_id": ["c1", "c2"],
            "x_center_m": [10_100.0, 90_500.0],
            "y_center_m": [10_000.0, 90_000.0],
        },
        geometry=[Point(10_100, 10_000), Point(90_500, 90_000)],
        crs=WORK_CRS,
    )
    table, pred, nodes = r.nearest_sources(graph, cells, sources, "apta")
    c1 = table.iloc[0]
    assert c1["road_km"] == pytest.approx(0.1 + 20 + 0.5)  # last mile + 20 km road + access
    assert c1["straight_km"] == pytest.approx(np.hypot(10.1, 10.0), rel=1e-6)
    c2 = table.iloc[1]  # near an isolated road: snaps to the main network instead
    assert c2["last_mile_km"] == pytest.approx(np.hypot(80.5, 80.0), rel=1e-3)
    assert np.isfinite(c2["road_km"])
    route = graph.path(pred, nodes[0])
    assert route.length == pytest.approx(20_000)


def test_scenarios_filter_classes(graph: r.RoadGraph) -> None:
    sources = gpd.GeoDataFrame(
        {"rock_source_id": ["A", "M"], "final_class": ["Apta", "Mixta"], "access_km": [0.0, 0.0]},
        geometry=[Point(0, 0), Point(10_000, 10_000)],
        crs=WORK_CRS,
    )
    cells = gpd.GeoDataFrame(
        {"cell_id": ["c"], "x_center_m": [10_000.0], "y_center_m": [9_000.0]},
        geometry=[Point(10_000, 9_000)],
        crs=WORK_CRS,
    )
    base, _, _ = r.nearest_sources(graph, cells, sources, "apta")
    sens, _, _ = r.nearest_sources(graph, cells, sources, "apta_mixta")
    assert base.iloc[0]["rock_source_id"] == "A"
    assert sens.iloc[0]["rock_source_id"] == "M"
