"""F6: deterministic net CO2 removal per cell (plan §5.1-5.3; decision D-56).

For every candidate cell, with the base values of the parameter registry (one scenario per grain
class; base = medium)::

    cdr_gross  = R_CO2(rock) * f_diss(rock, P80, T_cell, horizon) * (1 - f_loss(pH))   t CO2/t
    e_grind    = kWh/t(grain) * grid factor
    e_transport= road_km * truck L/(t km) * empty-return factor * diesel factor
    e_spread   = L/t * diesel factor
    net        = cdr_gross - e_grind - e_transport - e_spread                         t CO2/t
    net_ha     = net * application rate / horizon                                     t CO2/ha/yr
    breakeven  = (cdr_gross - e_grind - e_spread) / (emission per t km)                    km
    margin     = breakeven - road_km                                                  km

Candidate cell (D-56 defaults, configurable per scenario, D-58): protected < 50 %, frontier
"No condicionada" >= 50 %, agricultural use >= 50 % (optionally counting natural grassland /
savanna), slope > 12 % on < 50 % of the cell (all as shares of the cell). Rock class of a source:
ultramafic flag -> ultramafic; gabbro/norite named first -> gabbro (basalt kinetics and chemistry
as proxy, D-49/D-52); otherwise basalt. Q-Vm and J-Vi sources carry an "arc_volcanic_source" flag
(arc rocks may capture 3-5x less, Ryan et al. 2024 via R03a, unverified). Route scenario: Apta
sources only. Each cell inherits the health risk of its source's rock unit (``pending`` until the
health research is in, D-61). Results are internal until the SGC answers (D-08): no
results.json yet.
"""

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import geopandas as gpd
import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from mrv_lab import io  # noqa: E402
from mrv_lab.erw_siting import capture, history, soil_losses, weathering  # noqa: E402
from mrv_lab.erw_siting import database as db  # noqa: E402

#: Candidate-filter settings (D-56 defaults; every one can change per scenario, D-58):
#: share thresholds of the cell, frontier types, whether natural grassland / savanna counts as
#: agricultural use, and the slope class (8 or 12 %).
DEFAULT_FILTERS: dict = {
    "protected_max_frac": 0.5,
    "frontier_types": ["unconditioned"],  # add "conditioned" to include UPRA "Condicionada"
    "frontier_min_frac": 0.5,
    "land_use_min_frac": 0.5,
    "include_grassland": False,  # MapBiomas class 12 (Llanos savanna with extensive grazing)
    "slope_threshold_pct": 12,  # 8 or 12 (columns slope_gt8_frac / slope_gt12_frac)
    "slope_max_frac": 0.5,
}
ARC_VOLCANIC_UNITS = frozenset({"Q-Vm", "J-Vi"})
GABBRO_TYPES = ("gabbro", "norite")
OXIDES = ("CaO", "MgO", "Na2O", "K2O")
ROUTE_SCENARIO = "apta"
#: scenario id -> grain class; the registry's ``base`` scenario is the medium grain (D-56).
GRAIN_SCENARIOS = {db.BASE_SCENARIO: "medium", "grain_coarse": "coarse", "grain_fine": "fine"}


def candidates(filters: pd.DataFrame, settings: dict | None = None) -> pd.DataFrame:
    """``cell_id``, ``candidate`` (0/1) and ``excluded_by`` (failed rules, ';'-joined).

    ``settings`` overrides :data:`DEFAULT_FILTERS` key by key.
    """
    s = {**DEFAULT_FILTERS, **(settings or {})}
    frontier = sum(filters[f"frontier_{kind}_frac"].fillna(0) for kind in s["frontier_types"])
    land_use = filters["agro_use_frac"].fillna(0)
    if s["include_grassland"]:
        land_use = land_use + filters["grassland_frac"].fillna(0)
    checks = {
        "protected": filters["protected_frac"] < s["protected_max_frac"],
        "frontier": frontier >= s["frontier_min_frac"],
        "land_use": land_use >= s["land_use_min_frac"],
        "slope": filters[f"slope_gt{s['slope_threshold_pct']}_frac"] < s["slope_max_frac"],
    }
    failed = [np.where(ok.fillna(False), "", label) for label, ok in checks.items()]
    excluded = [";".join(f for f in row if f) for row in zip(*failed, strict=True)]
    return pd.DataFrame(
        {
            "cell_id": filters["cell_id"].to_numpy(),
            "candidate": [int(e == "") for e in excluded],
            "excluded_by": [e or None for e in excluded],
        }
    )


def rock_class(units: pd.DataFrame) -> pd.Series:
    """Rock class per ``unit_code`` from the F2 unit table (``rock_types``, ``ultramafic``)."""

    def classify(row: pd.Series) -> str:
        if int(row["ultramafic"]) == 1:
            return "ultramafic"
        first = (row["rock_types"] or "").split(";")[0].strip()
        return "gabbro" if first in GABBRO_TYPES else "basalt"

    return units.set_index("unit_code").apply(classify, axis=1).rename("rock_class")


def load_inputs(
    path: Path | None = None,
    settings: dict | None = None,
    route_scenario: str = "apta",
    temperature_variable: str = "t2m_mean_c",
) -> pd.DataFrame:
    """One row per cell: filters, temperature, pH, dry months, route and source rock class."""
    path = path or db.database_path()
    db.migrate(path)
    with db.connect(path) as con:
        cells = pd.read_sql("SELECT cell_id, department FROM cells", con)
        filters = pd.read_sql("SELECT * FROM cell_filters", con)
        values = pd.read_sql(
            "SELECT cell_id, variable, value FROM cell_values WHERE statistic = 'mean' "
            "AND variable IN (?, 'phh2o', 'dry_months')",
            con,
            params=(temperature_variable,),
        ).pivot_table(index="cell_id", columns="variable", values="value", aggfunc="first")
        values = values.rename(columns={temperature_variable: "t2m_mean_c"})
        routes = pd.read_sql(
            "SELECT cell_id, rock_source_id, road_km FROM cell_routes WHERE scenario = ?",
            con,
            params=(route_scenario,),
        )
        sources = pd.read_sql(
            "SELECT s.rock_source_id, u.unit_code, u.symbol, u.rock_types, u.ultramafic, "
            "u.health_risk FROM rock_sources s JOIN rock_units u USING (unit_code)",
            con,
        )
    classes = rock_class(sources.drop_duplicates("unit_code"))
    sources["rock_class"] = sources["unit_code"].map(classes)
    sources["arc_volcanic"] = sources["symbol"].isin(ARC_VOLCANIC_UNITS)
    frame = (
        cells.merge(candidates(filters, settings), on="cell_id")
        .merge(values.reset_index(), on="cell_id", how="left")
        .merge(routes, on="cell_id", how="left")
        .merge(
            sources[["rock_source_id", "rock_class", "arc_volcanic", "health_risk"]],
            on="rock_source_id",
            how="left",
        )
    )
    return frame


def chain(
    rock: np.ndarray,
    temp_c: np.ndarray,
    ph: np.ndarray,
    road_km: np.ndarray,
    values: dict[str, float],
    grain: str,
) -> dict[str, np.ndarray]:
    """The net-removal chain on plain arrays (one entry per cell); rock = class name or None.

    Shared by F6 (:func:`compute`) and the F7 Monte Carlo, which calls it once per draw.
    """
    v = values
    n = len(rock)
    cdr_max = np.full(n, np.nan)
    f_diss = np.full(n, np.nan)
    for cls in ("basalt", "gabbro", "ultramafic"):
        rows = rock == cls
        if not rows.any():
            continue
        oxides = {ox: v[f"{ox.lower()}_wt_pct_{cls}"] for ox in OXIDES}
        cdr_max[rows] = capture.capture_potential_t_co2_per_t(
            oxides, v["eta_mol_co2_per_mol_charge"]
        )
        kin = weathering.KINETIC_ROCK[cls]
        log10_wr = v[f"log10_wr_{kin}_mol_m2_s"]
        if kin == "ultramafic":  # partly serpentinized (D-57)
            log10_wr = weathering.effective_log10_wr(
                log10_wr,
                v["serpentinized_fraction_ultramafic"],
                v["log10_rate_ratio_serpentine_forsterite"],
            )
        f_diss[rows] = weathering.dissolved_fraction(
            p80_um=v[f"p80_um_{grain}"],
            years=v["horizon_years"],
            temperature_c=temp_c[rows],
            log10_wr_mol_m2_s=log10_wr,
            molar_mass_g_per_mol=v[f"molar_mass_{kin}_g_per_mol"],
            ea_kj_per_mol=v[f"activation_energy_kj_per_mol_{kin}"],
            reference_c=v["reference_temperature_c"],
            ssa_coef=v["ssa_coef_m2_per_g"],
            ssa_exponent=v["ssa_exponent"],
        )
    f_loss = soil_losses.loss_fraction(
        ph, v["acid_soil_ph_threshold"], v["f_loss_acid_soil"], v["f_loss_neutral_soil"]
    )
    diesel_t_per_l = v["diesel_ef_kgco2_per_l"] / 1000
    per_t_km = v["truck_l_diesel_per_t_km"] * v["empty_return_factor"] * diesel_t_per_l
    gross = cdr_max * f_diss * (1 - f_loss)
    e_grind = np.full(n, v[f"grinding_kwh_per_t_{grain}"] * v["grid_ef_kgco2_per_kwh"] / 1000)
    e_spread = np.full(n, v["spreading_l_diesel_per_t"] * diesel_t_per_l)
    e_transport = road_km * per_t_km
    net = gross - e_grind - e_transport - e_spread
    return {
        "cdr_max_tco2_per_t": cdr_max,
        "f_diss": f_diss,
        "f_loss": f_loss,
        "cdr_gross_tco2_per_t": gross,
        "e_grind_tco2_per_t": e_grind,
        "e_transport_tco2_per_t": e_transport,
        "e_spread_tco2_per_t": e_spread,
        "breakeven_km": (gross - e_grind - e_spread) / per_t_km,
        "net_tco2_per_t": net,
    }


def compute(frame: pd.DataFrame, values: dict[str, float], grain: str) -> pd.DataFrame:
    """Net-removal chain for the candidate cells of ``frame`` (others get only the filter)."""
    v = values
    out = frame[["cell_id", "candidate", "excluded_by"]].copy()
    cand = frame["candidate"].to_numpy() == 1
    rock = frame["rock_class"].where(cand)
    ph = frame["phh2o"].to_numpy(dtype="float64")
    road_km = np.where(cand, frame["road_km"].to_numpy(dtype="float64"), np.nan)
    res = chain(
        rock.to_numpy(dtype=object),
        frame["t2m_mean_c"].to_numpy(dtype="float64"),
        np.where(cand, ph, np.nan),
        road_km,
        v,
        grain,
    )
    for key in ("e_grind_tco2_per_t", "e_spread_tco2_per_t"):
        res[key] = np.where(cand, res[key], np.nan)
    out["rock_source_id"] = frame["rock_source_id"].where(cand)
    out["rock_class"] = rock
    out["road_km"] = road_km
    for key in (
        "cdr_max_tco2_per_t",
        "f_diss",
        "f_loss",
        "cdr_gross_tco2_per_t",
        "e_grind_tco2_per_t",
        "e_transport_tco2_per_t",
        "e_spread_tco2_per_t",
        "breakeven_km",
    ):
        out[key] = res[key]
    out["margin_km"] = out["breakeven_km"] - out["road_km"]
    out["net_tco2_per_t"] = res["net_tco2_per_t"]
    out["net_ha_tco2_per_ha_yr"] = (
        res["net_tco2_per_t"] * v["application_rate_t_per_ha"] / v["horizon_years"]
    )
    out["lime_demand"] = np.where(cand, (ph < v["acid_soil_ph_threshold"]).astype(int), None)
    out["ultramafic_source"] = np.where(cand, (rock == "ultramafic").astype(int), None)
    out["source_health_risk"] = frame["health_risk"].where(cand) if "health_risk" in frame else None
    out["data_quality"] = _flags(frame, cand)
    return out


def _flags(frame: pd.DataFrame, cand: np.ndarray) -> list[str | None]:
    """';'-joined data-quality flags of the candidate cells."""
    flags = []
    for is_cand, row in zip(cand, frame.itertuples(index=False), strict=True):
        if not is_cand:
            flags.append(None)
            continue
        f = []
        if row.rock_class == "gabbro":
            f.append("gabbro_proxy")
        if bool(row.arc_volcanic):
            f.append("arc_volcanic_source")
        if pd.notna(row.dry_months) and row.dry_months > 0:
            f.append(f"dry_months:{row.dry_months:.0f}")
        if pd.isna(row.road_km):
            f.append("no_route")
        if pd.isna(row.phh2o) or pd.isna(row.t2m_mean_c):
            f.append("missing_soil_or_climate")
        flags.append(";".join(f) or None)
    return flags


def _code_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=io.repo_root(), capture_output=True, text=True
        )
        return result.stdout.strip() or None
    except OSError:
        return None


def run_scenario(
    frame: pd.DataFrame,
    scenario_id: str,
    name: str,
    grain: str,
    path: Path,
    overrides: dict[str, float] | None = None,
    filters: dict | None = None,
    route_scenario: str = ROUTE_SCENARIO,
    notes: str = "F6 deterministic (D-56); internal until SGC answers (D-08)",
) -> tuple[pd.DataFrame, dict[str, float]]:
    """Add the scenario (if new), compute ``frame`` with its values, store ``runs`` and
    ``cell_results`` rows (run_id = f"f6_{scenario_id}"); returns the table and the values."""
    with db.connect(path) as con:
        exists = con.execute(
            "SELECT 1 FROM scenarios WHERE scenario_id = ?", (scenario_id,)
        ).fetchone()
    if not exists:
        changed_filters = filters if filters and filters != DEFAULT_FILTERS else None
        db.add_scenario(
            scenario_id,
            name,
            overrides=overrides,
            grain_class=grain,
            route_scenario=route_scenario,
            filters=changed_filters,
            path=path,
        )
    values = db.scenario_values(scenario_id, path).set_index("parameter_id")["value"]
    values = {k: float(x) for k, x in values.dropna().items()}
    table = compute(frame, values, grain)
    run_id = f"f6_{scenario_id}"
    db.append_rows(
        "runs",
        pd.DataFrame(
            [
                {
                    "run_id": run_id,
                    "scenario_id": scenario_id,
                    "created_utc": datetime.now(UTC).isoformat(timespec="seconds"),
                    "code_commit": _code_commit(),
                    "parameters_json": json.dumps(
                        {
                            "values": values,
                            "grain_class": grain,
                            "route_scenario": route_scenario,
                            "filters": filters or DEFAULT_FILTERS,
                        }
                    ),
                    "seed": None,
                    "notes": notes,
                }
            ]
        ),
        path,
    )
    db.append_rows("cell_results", table.assign(run_id=run_id), path)
    return table, values


def run(
    path: Path | None = None, settings: dict | None = None
) -> tuple[pd.DataFrame, dict[str, Path]]:
    """Compute and store one run per grain scenario (clearing earlier runs); write QC.

    ``settings``: candidate-filter overrides (:data:`DEFAULT_FILTERS`, D-58).
    """
    path = path or db.database_path()
    filters = {**DEFAULT_FILTERS, **(settings or {})}
    frame = load_inputs(path, filters)
    with db.connect(path) as con:
        con.execute("DELETE FROM cell_results")
        con.execute("DELETE FROM runs")
    results, base_values = [], {}
    for scenario_id, grain in GRAIN_SCENARIOS.items():
        table, values = run_scenario(
            frame,
            scenario_id,
            f"Registry values (sourced), {grain} grain",
            grain,
            path,
            filters=filters,
        )
        if scenario_id == db.BASE_SCENARIO:
            base_values = values
        results.append(table.assign(scenario_id=scenario_id, grain_class=grain))
    combined = pd.concat(results, ignore_index=True).merge(
        frame[["cell_id", "department"]], on="cell_id"
    )
    paths = save_qc(combined, path, frame, base_values)
    history.snapshot([paths["summary"]])
    return combined, paths


def summary(combined: pd.DataFrame) -> pd.DataFrame:
    """Per scenario and department: candidates, share net > 0, medians (internal QC)."""
    cand = combined[combined["candidate"] == 1]
    groups = cand.groupby(["scenario_id", "grain_class", "department"])
    table = groups.agg(
        candidate_cells=("cell_id", "size"),
        share_net_positive=("net_tco2_per_t", lambda s: float((s > 0).mean())),
        median_net_tco2_per_t=("net_tco2_per_t", "median"),
        median_net_tco2_per_ha_yr=("net_ha_tco2_per_ha_yr", "median"),
        median_road_km=("road_km", "median"),
        median_breakeven_km=("breakeven_km", "median"),
        share_acid=("lime_demand", lambda s: float(pd.to_numeric(s).mean())),
        share_ultramafic=("ultramafic_source", lambda s: float(pd.to_numeric(s).mean())),
    )
    return table.reset_index().round(4)


NOT_CANDIDATE_GREY = "#BDBDBD"
EMISSION_PARTS = {
    "e_grind_tco2_per_t": "Grinding",
    "e_transport_tco2_per_t": "Transport",
    "e_spread_tco2_per_t": "Spreading",
}
FILTER_LABELS = {
    "protected": "Protected area (RUNAP)",
    "frontier": "Outside the agricultural frontier (UPRA)",
    "land_use": "Not agricultural use (MapBiomas)",
    "slope": "Slope above threshold",
}


def save_qc(
    combined: pd.DataFrame,
    path: Path,
    frame: pd.DataFrame | None = None,
    base_values: dict[str, float] | None = None,
) -> dict[str, Path]:
    """Internal QC (D-08): summary table; candidate maps (net per ha, margin, emissions);
    exclusion-reason maps; and, when ``frame`` and ``base_values`` are given, "potential" maps
    computed for every cell as if it were farmland, with candidate cells outlined (D-58)."""
    qc = io.interim_dir() / "erw_siting" / "qc"
    qc.mkdir(parents=True, exist_ok=True)
    paths = {"summary": qc / "f6_summary.csv"}
    summary(combined).to_csv(paths["summary"], index=False)

    cells = gpd.read_file(path, layer="cells")[["cell_id", "geometry"]]
    depts = gpd.read_file(io.interim_dir() / "erw_siting" / "pilot_departments.gpkg").to_crs(
        cells.crs
    )
    base = cells.merge(combined[combined["scenario_id"] == db.BASE_SCENARIO], on="cell_id")
    cand = base[base["candidate"] == 1].copy()
    cand["e_total_kgco2_per_t"] = cand[list(EMISSION_PARTS)].sum(axis=1) * 1000
    outline = gpd.GeoSeries([cand.geometry.union_all()], crs=cells.crs)

    for column, label, name, cmap in (
        ("net_ha_tco2_per_ha_yr", "Net removal, t CO2/ha/yr", "f6_net_ha", "RdBu"),
        ("margin_km", "Break-even distance minus road distance, km", "f6_margin_km", "RdBu"),
        (
            "e_total_kgco2_per_t",
            "Grinding + transport + spreading, kg CO2/t",
            "f6_emissions_map",
            "RdYlGn_r",
        ),
    ):
        fig, ax = plt.subplots(figsize=(10, 6.5))
        base[base["candidate"] == 0].plot(ax=ax, color=NOT_CANDIDATE_GREY, linewidth=0)
        _plot_values(ax, cand, column, label, cmap)
        _decorate(ax, depts, f"QC — {label}, medium grain; dark grey = not candidate — internal")
        paths[name] = _save(fig, qc / f"{name}.png")

    paths["f6_emissions_parts"] = _emission_parts(cand, qc)
    paths["f6_exclusion_reasons"] = _exclusion_maps(base, depts, qc)

    if frame is not None and base_values is not None:
        potential = compute(frame.assign(candidate=1, excluded_by=None), base_values, "medium")
        potential["e_total_kgco2_per_t"] = potential[list(EMISSION_PARTS)].sum(axis=1) * 1000
        pot = cells.merge(potential, on="cell_id")
        for column, label, name, cmap in (
            (
                "e_total_kgco2_per_t",
                "Emissions if farmed, kg CO2/t rock",
                "f6_potential_emissions",
                "RdYlGn_r",
            ),
            ("margin_km", "Margin if farmed, km", "f6_potential_margin_km", "RdBu"),
            (
                "net_ha_tco2_per_ha_yr",
                "Net removal if farmed, t CO2/ha/yr",
                "f6_potential_net_ha",
                "RdBu",
            ),
        ):
            fig, ax = plt.subplots(figsize=(10, 6.5))
            _plot_values(ax, pot, column, label, cmap)
            outline.boundary.plot(ax=ax, color="black", linewidth=0.4)
            _decorate(
                ax, depts, f"QC — {label}, every cell; black outline = candidate cells — internal"
            )
            paths[name] = _save(fig, qc / f"{name}.png")
    return paths


def _plot_values(ax, gdf: gpd.GeoDataFrame, column: str, label: str, cmap: str) -> None:  # noqa: ANN001
    """Diverging maps centred on 0; sequential (emissions) clipped at the 2nd-98th percentiles."""
    values = gdf[column]
    if cmap == "RdBu":
        # Colour range from non-ultramafic cells (ultramafic sources would wash out the rest).
        ref = values[gdf["rock_class"] != "ultramafic"] if "rock_class" in gdf else values
        ref = ref if ref.notna().any() else values
        limit = float(np.nanpercentile(np.abs(ref), 95)) or 1.0
        vmin, vmax = -limit, limit
    else:
        vmin, vmax = (float(np.nanpercentile(values, q)) for q in (2, 98))
    gdf.plot(
        ax=ax,
        column=column,
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
        linewidth=0,
        legend=True,
        legend_kwds={"label": label, "shrink": 0.6},
        missing_kwds={"color": "white"},
    )


def _decorate(ax, depts: gpd.GeoDataFrame, title: str) -> None:  # noqa: ANN001
    """Department outlines and names, title, no axes."""
    depts.boundary.plot(ax=ax, color="black", linewidth=0.9)
    for _, row in depts.iterrows():
        point = row.geometry.representative_point()
        ax.annotate(
            row["name"],
            (point.x, point.y),
            ha="center",
            fontsize=8,
            fontweight="bold",
            bbox={"boxstyle": "round,pad=0.2", "fc": "white", "ec": "none", "alpha": 0.7},
        )
    ax.set_title(title, fontsize=9)
    ax.set_axis_off()


def _save(fig, out: Path) -> Path:  # noqa: ANN001
    fig.savefig(out, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return out


def _emission_parts(cand: pd.DataFrame, qc: Path) -> Path:
    """Median grinding / transport / spreading per department (stacked bars)."""
    medians = cand.groupby("department")[list(EMISSION_PARTS)].median() * 1000
    fig, ax = plt.subplots(figsize=(7, 3.5))
    left = np.zeros(len(medians))
    for (column, label), color in zip(
        EMISSION_PARTS.items(), ("#999999", "#D55E00", "#56B4E9"), strict=True
    ):
        ax.barh(medians.index, medians[column], left=left, color=color, label=label)
        left += medians[column].to_numpy()
    ax.set_xlabel("Median emissions, kg CO2 per t rock (medium grain)")
    ax.set_title("QC — what drives the emissions in each department — internal", fontsize=9)
    ax.legend(frameon=False, fontsize=8)
    return _save(fig, qc / "f6_emissions_parts.png")


def _exclusion_maps(base: gpd.GeoDataFrame, depts: gpd.GeoDataFrame, qc: Path) -> Path:
    """2 x 2 panels: cells failing each candidate filter (a cell can fail several)."""
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    reasons = base["excluded_by"].fillna("")
    for ax, (key, label) in zip(axes.ravel(), FILTER_LABELS.items(), strict=True):
        fails = reasons.str.split(";").apply(lambda r, k=key: k in r)
        base[~fails].plot(ax=ax, color="#EEEEEE", linewidth=0)
        base[fails].plot(ax=ax, color="#D55E00", linewidth=0)
        share = fails.groupby(base["department"]).mean()
        text = ", ".join(f"{d[:6]} {s:.0%}" for d, s in share.items())
        _decorate(ax, depts, f"{label}\n(cells failing: {text})")
    fig.suptitle("QC — why cells are not candidates (orange = fails this filter) — internal")
    return _save(fig, qc / "f6_exclusion_reasons.png")
