"""F7 part B: assumption scenarios (decision D-60), deterministic, medium grain.

1. horizon 30 years instead of 10;
2. UPRA "Condicionada" frontier counted as candidate land;
3. slope class 8 % instead of 12 %;
4. Apta + Mixta rock sources;
5. Meta without its main rock unit (the unit that supplies most Meta candidate cells in the base
   run): its sources are removed and every cell is re-routed.

Each scenario is stored as a ``scenarios`` row (overrides / filters / route scenario) with its run
in ``runs`` and ``cell_results``; a summary per department goes to the internal QC folder.
"""

from pathlib import Path

import geopandas as gpd
import pandas as pd

from mrv_lab import io
from mrv_lab.erw_siting import database as db
from mrv_lab.erw_siting import net_removal as nr
from mrv_lab.erw_siting import quarries, routing

META_MAIN_ROUTE = "apta_no_meta_main"

#: id -> (name, parameter overrides, filter settings, route scenario)
SCENARIOS: dict[str, tuple[str, dict | None, dict | None, str]] = {
    "s1_horizon_30": ("Horizon 30 years", {"horizon_years": 30.0}, None, "apta"),
    "s2_conditioned_frontier": (
        "Frontier: No condicionada + Condicionada",
        None,
        {"frontier_types": ["unconditioned", "conditioned"]},
        "apta",
    ),
    "s3_slope_8": ("Slope class 8 %", None, {"slope_threshold_pct": 8}, "apta"),
    "s4_apta_mixta": ("Apta + Mixta rock sources", None, None, "apta_mixta"),
    "s5_meta_without_main_unit": ("Meta without its main rock unit", None, None, META_MAIN_ROUTE),
}


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


def reroute_without_unit(path: Path, unit_code: int, route_name: str = META_MAIN_ROUTE) -> None:
    """Road routes to the nearest Apta source excluding one rock unit (stored as ``route_name``)."""
    graph = routing.RoadGraph(quarries.read_truck_roads(quarries.fetch_roads()).geometry)
    cells = gpd.read_file(path, layer="cells")
    sources = gpd.read_file(path, layer="rock_sources")
    kept = sources[sources["unit_code"] != unit_code]
    table, _, _ = routing.nearest_sources(graph, cells, kept, "apta")
    table["scenario"] = route_name
    with db.connect(path) as con:
        con.execute("DELETE FROM cell_routes WHERE scenario = ?", (route_name,))
    db.append_rows("cell_routes", table, path)


def run(path: Path | None = None) -> dict[str, Path]:
    """Run the five assumption scenarios (medium grain) and write the summary table."""
    path = path or db.database_path()
    with db.connect(path) as con:
        old = [r[0] for r in con.execute("SELECT run_id FROM runs WHERE run_id LIKE 'f6_s%'")]
        for run_id in old:
            con.execute("DELETE FROM cell_results WHERE run_id = ?", (run_id,))
            con.execute("DELETE FROM runs WHERE run_id = ?", (run_id,))
    unit = meta_main_unit(path)
    reroute_without_unit(path, unit)
    tables = []
    for scenario_id, (name, overrides, settings, route) in SCENARIOS.items():
        filters = {**nr.DEFAULT_FILTERS, **(settings or {})}
        frame = nr.load_inputs(path, filters, route)
        table, _ = nr.run_scenario(
            frame,
            scenario_id,
            name,
            "medium",
            path,
            overrides=overrides,
            filters=filters,
            route_scenario=route,
            notes=f"F7 assumption scenario (D-60); Meta main unit = {unit}",
        )
        tables.append(
            table.assign(scenario_id=scenario_id, grain_class="medium").merge(
                frame[["cell_id", "department"]], on="cell_id"
            )
        )
    qc = io.interim_dir() / "erw_siting" / "qc"
    qc.mkdir(parents=True, exist_ok=True)
    out = qc / "f7_assumptions.csv"
    nr.summary(pd.concat(tables, ignore_index=True)).assign(meta_main_unit=unit).to_csv(
        out, index=False
    )
    return {"f7_assumptions": out}
