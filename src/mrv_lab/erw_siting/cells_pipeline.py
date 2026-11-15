"""F5 orchestration: build the cell grid, fill the GeoPackage, route every cell, QC outputs.

Outputs (gitignored): ``erw_siting.gpkg`` tables ``cells``, ``cell_filters``, ``cell_values``,
``cell_routes`` (two scenarios), ``sources``; QC maps of road distance (with 20 example routes) and
of source influence areas; QC table of distances per department.
"""

from pathlib import Path

import geopandas as gpd
import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from mrv_lab import io  # noqa: E402
from mrv_lab.erw_siting import database as db  # noqa: E402
from mrv_lab.erw_siting import grid as g  # noqa: E402
from mrv_lab.erw_siting import quarries, routing  # noqa: E402
from mrv_lab.erw_siting.regions import WORK_CRS  # noqa: E402

N_EXAMPLE_ROUTES = 20
SEED = 42

#: Source registry rows for the ``sources`` table (full details in data/SOURCES.md).
SOURCES = [
    ("D4", "UPRA agricultural frontier", "https://geoservicios.upra.gov.co", "CC BY-SA 4.0", "yes"),
    (
        "D6",
        "MapBiomas Colombia Collection 3.0 (2024)",
        "https://colombia.mapbiomas.org",
        "CC BY 4.0",
        "yes",
    ),
    (
        "D8",
        "ISRIC SoilGrids 2.0",
        "https://files.isric.org/soilgrids/latest/data/",
        "CC BY 4.0",
        "yes",
    ),
    (
        "D9",
        "CHIRPS v2.0 monthly",
        "https://data.chc.ucsb.edu/products/CHIRPS/v2.0/",
        "Public domain",
        "yes",
    ),
    (
        "D10",
        "ERA5-Land monthly means (2 m temperature)",
        "https://cds.climate.copernicus.eu",
        "CC BY 4.0",
        "yes",
    ),
    (
        "D11",
        "Copernicus DEM GLO-30",
        "https://copernicus-dem-30m.s3.amazonaws.com",
        "Copernicus WorldDEM-30 licence",
        "yes",
    ),
    (
        "D12",
        "OpenStreetMap roads (HOT export)",
        "https://data.humdata.org/dataset/hotosm_col_roads",
        "ODbL 1.0",
        "yes",
    ),
    (
        "D18",
        "RUNAP protected areas",
        "https://storage.googleapis.com/pnn_geodatabase/runap/",
        "CC BY-SA 4.0",
        "yes",
    ),
    (
        "D19",
        "ERA5-Land monthly means (total evaporation)",
        "https://cds.climate.copernicus.eu",
        "CC BY 4.0",
        "yes",
    ),
]


def run(pilot: gpd.GeoDataFrame, path: Path | None = None) -> dict[str, Path]:
    """Run F5 end to end and return the QC output paths."""
    path = path or db.database_path()
    grid, cells, rows, cols = g.build_cells(pilot)
    ids = list(cells["cell_id"])
    db.write_cells(cells, path)
    db.write_table(
        "sources",
        pd.DataFrame(SOURCES, columns=["source_id", "name", "url", "license", "redistribution"]),
        path,
    )
    db.write_table("cell_filters", g.cell_filters(grid, rows, cols, pilot, ids), path)
    db.write_table("cell_values", g.cell_values(grid, rows, cols, pilot, ids), path)

    roads = quarries.read_truck_roads(quarries.fetch_roads())
    graph = routing.RoadGraph(roads.geometry)
    sources = gpd.read_file(path, layer="rock_sources")
    tables, base_pred, base_nodes = [], None, None
    for scenario in routing.SCENARIOS:
        table, pred, nodes = routing.nearest_sources(graph, cells, sources, scenario)
        tables.append(table)
        if scenario == "apta":
            base_pred, base_nodes = pred, nodes
    routes = pd.concat(tables, ignore_index=True)
    db.write_table("cell_routes", routes, path)
    return save_qc(cells, routes, sources, graph, base_pred, base_nodes, pilot)


def save_qc(cells, routes, sources, graph, pred, nodes, pilot) -> dict[str, Path]:  # noqa: ANN001
    """Distance map with example routes, influence-area map and distance table."""
    qc = io.interim_dir() / "erw_siting" / "qc"
    qc.mkdir(parents=True, exist_ok=True)
    base = routes[routes["scenario"] == "apta"].reset_index(drop=True)
    gdf = cells.merge(base, on="cell_id")

    rng = np.random.default_rng(SEED)
    pick = rng.choice(np.flatnonzero(gdf["road_km"].notna()), N_EXAMPLE_ROUTES, replace=False)
    examples = gpd.GeoDataFrame(
        {
            "cell_id": gdf.loc[pick, "cell_id"].to_numpy(),
            "road_km": gdf.loc[pick, "road_km"].round(1).to_numpy(),
        },
        geometry=[graph.path(pred, int(nodes[i])) for i in pick],
        crs=WORK_CRS,
    )
    examples.to_file(io.interim_dir() / "erw_siting" / "example_routes.gpkg", driver="GPKG")

    paths = {}
    bounds = pilot.total_bounds
    fig, ax = plt.subplots(figsize=(9, 6))
    gdf.plot(
        ax=ax,
        column="road_km",
        cmap="viridis",
        legend=True,
        legend_kwds={"label": "Road distance to nearest Apta source (km)", "shrink": 0.6},
    )
    examples.plot(ax=ax, color="white", linewidth=1.2)
    examples.plot(ax=ax, color="black", linewidth=0.5)
    near = sources[sources["final_class"] == "Apta"]
    near.plot(ax=ax, color="red", markersize=3)
    pilot.boundary.plot(ax=ax, color="black", linewidth=0.8)
    ax.set_xlim(bounds[0] - 50_000, bounds[2] + 50_000)
    ax.set_ylim(bounds[1] - 50_000, bounds[3] + 50_000)
    ax.set_title(
        "QC — road distance to nearest potential Apta source, 20 example routes "
        f"({WORK_CRS}) — internal",
        fontsize=9,
    )
    ax.set_axis_off()
    paths["distance_map"] = qc / "routing_distance_apta.png"
    fig.savefig(paths["distance_map"], dpi=130, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 6))
    codes = pd.factorize(gdf["rock_source_id"])[0]
    gdf.assign(zone=np.where(codes < 0, np.nan, codes % 20)).plot(
        ax=ax, column="zone", cmap="tab20", missing_kwds={"color": "#DDDDDD"}
    )
    pilot.boundary.plot(ax=ax, color="black", linewidth=0.8)
    ax.set_title(
        "QC — influence areas: cells coloured by the Apta source that supplies them "
        "(colours repeat) — internal",
        fontsize=9,
    )
    ax.set_axis_off()
    paths["influence_map"] = qc / "routing_influence_apta.png"
    fig.savefig(paths["influence_map"], dpi=130, bbox_inches="tight")
    plt.close(fig)

    summary = (
        routes.merge(cells[["cell_id", "department"]], on="cell_id")
        .groupby(["scenario", "department"])
        .agg(
            cells=("cell_id", "size"),
            unreachable=("road_km", lambda s: int(s.isna().sum())),
            road_km_p10=("road_km", lambda s: s.quantile(0.1)),
            road_km_p50=("road_km", "median"),
            road_km_p90=("road_km", lambda s: s.quantile(0.9)),
            tortuosity_median=("road_km", "size"),
        )
    )
    ratio = (routes["road_km"] / routes["straight_km"]).replace(np.inf, np.nan)
    tort = (
        routes.assign(t=ratio)
        .merge(cells[["cell_id", "department"]], on="cell_id")
        .groupby(["scenario", "department"])["t"]
        .median()
    )
    summary["tortuosity_median"] = tort
    paths["table"] = qc / "routing_summary.csv"
    summary.round(2).to_csv(paths["table"])
    examples.drop(columns="geometry").to_csv(qc / "routing_example_routes.csv", index=False)
    return paths
