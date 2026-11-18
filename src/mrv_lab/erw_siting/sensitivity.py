"""F7 part B: assumption scenarios, deterministic (decisions D-60, D-62).

First round (medium grain): 1. horizon 30 years; 2. UPRA "Condicionada" frontier counted as
candidate land; 3. slope class 8 %; 4. Apta + Mixta rock sources; 5. Meta without its main rock
unit (the unit supplying most Meta candidate cells in the base run), re-routed.
Second round: 6. no ultramafic sources (Ni / Cr / asbestos concern), re-routed; 7. fine grain with
the comminution energy of Rinder & von Hagke 2021 (173 kWh/t to < 10 µm, Table 2); 8. recent
climate: mean temperature 1996-2025 (ERA5-Land) instead of 1991-2020.

Each scenario is a ``scenarios`` row (overrides / filters / route scenario) with its run in
``runs`` and ``cell_results``. Running a subset only replaces the runs of that subset; the summary
table covers every assumption run in the database and is copied to the history folder.
"""

from pathlib import Path

import geopandas as gpd
import pandas as pd
from rasterio.enums import Resampling

from mrv_lab import io
from mrv_lab.erw_siting import climate, history, literature, quarries, routing
from mrv_lab.erw_siting import database as db
from mrv_lab.erw_siting import grid as g
from mrv_lab.erw_siting import net_removal as nr

META_MAIN_ROUTE = "apta_no_meta_main"
NO_ULTRAMAFIC_ROUTE = "apta_no_ultramafic"
RECENT_T2M = "t2m_mean_c_1996_2025"

SOURCES: dict[str, dict] = {
    "rinder_von_hagke_2021": {
        "url": "https://www.remineralize.org/wp-content/uploads/2022/05/"
        "1-s2.0-S0959652621023969-main.pdf",
        "citation": "Rinder, T. & von Hagke, C. (2021). The influence of particle size on the "
        "potential of enhanced basalt weathering for carbon dioxide removal - Insights from a "
        "regional assessment. Journal of Cleaner Production 315, 128178",
        "doi": "doi:10.1016/j.jclepro.2021.128178",
        "locator": "Table 2: comminution (<10 µm) 173.0 kWh/t (citing Hangx & Spiers 2009)",
        "checks": [r"comminution \(<10 μm\)d?\s+173\.0", r"open access article under the CC BY"],
    },
}
RINDER_FINE_KWH_PER_T = 173.0

#: id -> (name, grain, parameter overrides, filter settings, route scenario, temperature variable)
SCENARIOS: dict[str, tuple[str, str, dict | None, dict | None, str, str]] = {
    "s1_horizon_30": (
        "Horizon 30 years",
        "medium",
        {"horizon_years": 30.0},
        None,
        "apta",
        "t2m_mean_c",
    ),
    "s2_conditioned_frontier": (
        "Frontier: No condicionada + Condicionada",
        "medium",
        None,
        {"frontier_types": ["unconditioned", "conditioned"]},
        "apta",
        "t2m_mean_c",
    ),
    "s3_slope_8": (
        "Slope class 8 %",
        "medium",
        None,
        {"slope_threshold_pct": 8},
        "apta",
        "t2m_mean_c",
    ),
    "s4_apta_mixta": (
        "Apta + Mixta rock sources",
        "medium",
        None,
        None,
        "apta_mixta",
        "t2m_mean_c",
    ),
    "s5_meta_without_main_unit": (
        "Meta without its main rock unit",
        "medium",
        None,
        None,
        META_MAIN_ROUTE,
        "t2m_mean_c",
    ),
    "s6_no_ultramafic": (
        "No ultramafic sources",
        "medium",
        None,
        None,
        NO_ULTRAMAFIC_ROUTE,
        "t2m_mean_c",
    ),
    "s7_fine_rinder_grinding": (
        "Fine grain, grinding energy of Rinder & von Hagke 2021",
        "fine",
        {"grinding_kwh_per_t_fine": RINDER_FINE_KWH_PER_T},
        None,
        "apta",
        "t2m_mean_c",
    ),
    "s8_recent_climate": ("Mean temperature 1996-2025", "medium", None, None, "apta", RECENT_T2M),
}


def verify_sources() -> list[str]:
    """Quoted numbers of the second round must appear in their source text."""
    return literature.verify(SOURCES, literature.texts(SOURCES, "sensitivity"))


def meta_main_unit(path: Path) -> int:
    """Rock unit that supplies most Meta candidate cells in the base F6 run."""
    with db.connect(path) as con:
        row = con.execute(
            "SELECT s.unit_code, COUNT(*) AS n FROM cell_results r "
            "JOIN cells c USING (cell_id) JOIN rock_sources s USING (rock_source_id) "
            "WHERE r.run_id = ? AND r.candidate = 1 AND c.department = 'Meta' "
            "GROUP BY s.unit_code ORDER BY n DESC LIMIT 1",
            (f"f6_{db.BASE_SCENARIO}",),
        ).fetchone()
    return int(row[0])


def ultramafic_units(path: Path) -> list[int]:
    """Rock units flagged ultramafic (F2)."""
    with db.connect(path) as con:
        return [r[0] for r in con.execute("SELECT unit_code FROM rock_units WHERE ultramafic = 1")]


def reroute_without_units(
    path: Path, unit_codes: list[int], route_name: str, graph: routing.RoadGraph | None = None
) -> routing.RoadGraph:
    """Road routes to the nearest Apta source excluding some rock units (stored as
    ``route_name`` in ``cell_routes``); returns the road graph for reuse."""
    graph = graph or routing.RoadGraph(quarries.read_truck_roads(quarries.fetch_roads()).geometry)
    cells = gpd.read_file(path, layer="cells")
    sources = gpd.read_file(path, layer="rock_sources")
    kept = sources[~sources["unit_code"].isin(unit_codes)]
    table, _, _ = routing.nearest_sources(graph, cells, kept, "apta")
    table["scenario"] = route_name
    with db.connect(path) as con:
        con.execute("DELETE FROM cell_routes WHERE scenario = ?", (route_name,))
    db.append_rows("cell_routes", table, path)
    return graph


def store_recent_temperature(path: Path) -> None:
    """Per-cell mean temperature 1996-2025 into ``cell_values`` (variable ``RECENT_T2M``)."""
    pilot = gpd.read_file(io.interim_dir() / "erw_siting" / "pilot_departments.gpkg")
    era5_dir = io.raw_dir() / "era5land"
    extra = climate.fetch_era5land_t2m_extra(pilot, era5_dir)
    files = climate.recent_temperature(pilot, era5_dir / "t2m_1991-2020_monthly.tif", extra)
    grid, cells, rows, cols = g.build_cells(pilot)
    ordered = [files[name] for name in pilot["name"]]
    values = g.raster_to_grid(ordered, grid, Resampling.bilinear)[rows, cols]
    table = pd.DataFrame(
        {
            "cell_id": cells["cell_id"].to_numpy(),
            "layer": "climate",
            "variable": RECENT_T2M,
            "statistic": "mean",
            "value": values,
            "unit": "°C",
            "source_id": "D10",
        }
    )
    with db.connect(path) as con:
        con.execute("DELETE FROM cell_values WHERE variable = ?", (RECENT_T2M,))
    db.append_rows("cell_values", table, path)


def run(path: Path | None = None, scenarios: list[str] | None = None) -> dict[str, Path]:
    """Run the given assumption scenarios (default: all) and write the summary table."""
    path = path or db.database_path()
    db.migrate(path)
    chosen = scenarios or list(SCENARIOS)
    if "s7_fine_rinder_grinding" in chosen:
        problems = verify_sources()
        if problems:
            raise ValueError(f"Rinder & von Hagke quote not found: {problems}")
    with db.connect(path) as con:
        for scenario_id in chosen:
            con.execute("DELETE FROM cell_results WHERE run_id = ?", (f"f6_{scenario_id}",))
            con.execute("DELETE FROM runs WHERE run_id = ?", (f"f6_{scenario_id}",))
    unit = meta_main_unit(path)
    graph = None
    if "s5_meta_without_main_unit" in chosen:
        graph = reroute_without_units(path, [unit], META_MAIN_ROUTE)
    if "s6_no_ultramafic" in chosen:
        reroute_without_units(path, ultramafic_units(path), NO_ULTRAMAFIC_ROUTE, graph)
    if "s8_recent_climate" in chosen:
        store_recent_temperature(path)
    for scenario_id in chosen:
        name, grain, overrides, settings, route, temperature = SCENARIOS[scenario_id]
        filters = {**nr.DEFAULT_FILTERS, **(settings or {})}
        frame = nr.load_inputs(path, filters, route, temperature)
        nr.run_scenario(
            frame,
            scenario_id,
            name,
            grain,
            path,
            overrides=overrides,
            filters=filters,
            route_scenario=route,
            notes=f"F7 assumption scenario (D-60, D-62); Meta main unit = {unit}",
        )
    out = io.interim_dir() / "erw_siting" / "qc" / "f7_assumptions.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    summary_all(path).assign(meta_main_unit=unit).to_csv(out, index=False)
    history.snapshot([out])
    return {"f7_assumptions": out}


def summary_all(path: Path) -> pd.DataFrame:
    """Department summary of every assumption run stored in the database."""
    with db.connect(path) as con:
        table = pd.read_sql(
            "SELECT r.*, ru.scenario_id, s.grain_class, c.department FROM cell_results r "
            "JOIN runs ru USING (run_id) JOIN scenarios s USING (scenario_id) "
            "JOIN cells c USING (cell_id) WHERE ru.run_id LIKE 'f6_s%'",
            con,
        )
    return nr.summary(table)
