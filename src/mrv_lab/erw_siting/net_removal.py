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

Candidate cell (D-56): protected < 50 %, frontier "No condicionada" >= 50 %, agricultural use
>= 50 %, slope > 12 % on < 50 % of the cell (all as shares of the cell). Rock class of a source:
ultramafic flag -> ultramafic; gabbro/norite named first -> gabbro (basalt kinetics and chemistry
as proxy, D-49/D-52); otherwise basalt. Q-Vm and J-Vi sources carry an "arc_volcanic_source" flag
(arc rocks may capture 3-5x less, Ryan et al. 2024 via R03a, unverified). Route scenario: Apta
sources only. Results are internal until the SGC answers (D-08): no results.json yet.
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
from mrv_lab.erw_siting import capture, soil_losses, weathering  # noqa: E402
from mrv_lab.erw_siting import database as db  # noqa: E402

#: Candidate rules (D-56): column, comparison, threshold, label used in ``excluded_by``.
FILTER_RULES = [
    ("protected_frac", "<", 0.5, "protected"),
    ("frontier_unconditioned_frac", ">=", 0.5, "frontier"),
    ("agro_use_frac", ">=", 0.5, "land_use"),
    ("slope_gt12_frac", "<", 0.5, "slope"),
]
ARC_VOLCANIC_UNITS = frozenset({"Q-Vm", "J-Vi"})
GABBRO_TYPES = ("gabbro", "norite")
OXIDES = ("CaO", "MgO", "Na2O", "K2O")
ROUTE_SCENARIO = "apta"
#: scenario id -> grain class; the registry's ``base`` scenario is the medium grain (D-56).
GRAIN_SCENARIOS = {db.BASE_SCENARIO: "medium", "grain_coarse": "coarse", "grain_fine": "fine"}


def candidates(filters: pd.DataFrame) -> pd.DataFrame:
    """``cell_id``, ``candidate`` (0/1) and ``excluded_by`` (failed rules, ';'-joined)."""
    failed = []
    for column, op, threshold, label in FILTER_RULES:
        values = filters[column]
        ok = values < threshold if op == "<" else values >= threshold
        failed.append(np.where(ok.fillna(False), "", label))
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


def load_inputs(path: Path | None = None) -> pd.DataFrame:
    """One row per cell: filters, temperature, pH, dry months, route and source rock class."""
    path = path or db.database_path()
    with db.connect(path) as con:
        cells = pd.read_sql("SELECT cell_id, department FROM cells", con)
        filters = pd.read_sql("SELECT * FROM cell_filters", con)
        values = pd.read_sql(
            "SELECT cell_id, variable, value FROM cell_values WHERE statistic = 'mean' "
            "AND variable IN ('t2m_mean_c', 'phh2o', 'dry_months')",
            con,
        ).pivot_table(index="cell_id", columns="variable", values="value", aggfunc="first")
        routes = pd.read_sql(
            "SELECT cell_id, rock_source_id, road_km FROM cell_routes WHERE scenario = ?",
            con,
            params=(ROUTE_SCENARIO,),
        )
        sources = pd.read_sql(
            "SELECT s.rock_source_id, u.unit_code, u.symbol, u.rock_types, u.ultramafic "
            "FROM rock_sources s JOIN rock_units u USING (unit_code)",
            con,
        )
    classes = rock_class(sources.drop_duplicates("unit_code"))
    sources["rock_class"] = sources["unit_code"].map(classes)
    sources["arc_volcanic"] = sources["symbol"].isin(ARC_VOLCANIC_UNITS)
    frame = (
        cells.merge(candidates(filters), on="cell_id")
        .merge(values.reset_index(), on="cell_id", how="left")
        .merge(routes, on="cell_id", how="left")
        .merge(
            sources[["rock_source_id", "rock_class", "arc_volcanic"]],
            on="rock_source_id",
            how="left",
        )
    )
    return frame


def compute(frame: pd.DataFrame, values: dict[str, float], grain: str) -> pd.DataFrame:
    """Net-removal chain for the candidate cells of ``frame`` (others get only the filter)."""
    v = values
    out = frame[["cell_id", "candidate", "excluded_by"]].copy()
    cand = frame["candidate"].to_numpy() == 1
    rock = frame["rock_class"].where(cand)
    temp = frame["t2m_mean_c"].to_numpy(dtype="float64")
    ph = frame["phh2o"].to_numpy(dtype="float64")
    road_km = frame["road_km"].to_numpy(dtype="float64")

    cdr_max = np.full(len(frame), np.nan)
    f_diss = np.full(len(frame), np.nan)
    for cls in ("basalt", "gabbro", "ultramafic"):
        rows = (rock == cls).to_numpy()
        if not rows.any():
            continue
        oxides = {ox: v[f"{ox.lower()}_wt_pct_{cls}"] for ox in OXIDES}
        cdr_max[rows] = capture.capture_potential_t_co2_per_t(
            oxides, v["eta_mol_co2_per_mol_charge"]
        )
        kin = weathering.KINETIC_ROCK[cls]
        f_diss[rows] = weathering.dissolved_fraction(
            p80_um=v[f"p80_um_{grain}"],
            years=v["horizon_years"],
            temperature_c=temp[rows],
            log10_wr_mol_m2_s=v[f"log10_wr_{kin}_mol_m2_s"],
            molar_mass_g_per_mol=v[f"molar_mass_{kin}_g_per_mol"],
            ea_kj_per_mol=v[f"activation_energy_kj_per_mol_{kin}"],
            reference_c=v["reference_temperature_c"],
            ssa_coef=v["ssa_coef_m2_per_g"],
            ssa_exponent=v["ssa_exponent"],
        )
    f_loss = soil_losses.loss_fraction(
        ph, v["acid_soil_ph_threshold"], v["f_loss_acid_soil"], v["f_loss_neutral_soil"]
    )
    f_loss = np.where(cand, f_loss, np.nan)
    diesel_t_per_l = v["diesel_ef_kgco2_per_l"] / 1000
    per_t_km = v["truck_l_diesel_per_t_km"] * v["empty_return_factor"] * diesel_t_per_l
    gross = cdr_max * f_diss * (1 - f_loss)
    e_grind = np.where(
        cand, v[f"grinding_kwh_per_t_{grain}"] * v["grid_ef_kgco2_per_kwh"] / 1000, np.nan
    )
    e_spread = np.where(cand, v["spreading_l_diesel_per_t"] * diesel_t_per_l, np.nan)
    e_transport = np.where(cand, road_km * per_t_km, np.nan)
    net = gross - e_grind - e_transport - e_spread
    breakeven = (gross - e_grind - e_spread) / per_t_km

    out["rock_source_id"] = frame["rock_source_id"].where(cand)
    out["rock_class"] = rock
    out["road_km"] = np.where(cand, road_km, np.nan)
    out["cdr_max_tco2_per_t"] = cdr_max
    out["f_diss"] = f_diss
    out["f_loss"] = f_loss
    out["cdr_gross_tco2_per_t"] = gross
    out["e_grind_tco2_per_t"] = e_grind
    out["e_transport_tco2_per_t"] = e_transport
    out["e_spread_tco2_per_t"] = e_spread
    out["breakeven_km"] = breakeven
    out["margin_km"] = breakeven - out["road_km"]
    out["net_tco2_per_t"] = net
    out["net_ha_tco2_per_ha_yr"] = net * v["application_rate_t_per_ha"] / v["horizon_years"]
    out["lime_demand"] = np.where(cand, (ph < v["acid_soil_ph_threshold"]).astype(int), None)
    out["ultramafic_source"] = np.where(cand, (rock == "ultramafic").astype(int), None)
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


def run(path: Path | None = None) -> tuple[pd.DataFrame, dict[str, Path]]:
    """Compute and store one run per grain scenario; write internal QC table and maps."""
    path = path or db.database_path()
    frame = load_inputs(path)
    with db.connect(path) as con:
        existing = {r[0] for r in con.execute("SELECT scenario_id FROM scenarios")}
        con.execute("DELETE FROM cell_results")
        con.execute("DELETE FROM runs")
    results = []
    for scenario_id, grain in GRAIN_SCENARIOS.items():
        if scenario_id not in existing:
            db.add_scenario(
                scenario_id,
                f"Registry values (sourced), {grain} grain",
                grain_class=grain,
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
                                "route_scenario": ROUTE_SCENARIO,
                                "filters": FILTER_RULES,
                            }
                        ),
                        "seed": None,
                        "notes": "F6 deterministic (D-56); internal until SGC answers (D-08)",
                    }
                ]
            ),
            path,
        )
        db.append_rows("cell_results", table.assign(run_id=run_id), path)
        results.append(table.assign(scenario_id=scenario_id, grain_class=grain))
    combined = pd.concat(results, ignore_index=True).merge(
        frame[["cell_id", "department"]], on="cell_id"
    )
    return combined, save_qc(combined, path)


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


def save_qc(combined: pd.DataFrame, path: Path) -> dict[str, Path]:
    """Internal QC: summary table and maps of net removal and margin (base scenario)."""
    qc = io.interim_dir() / "erw_siting" / "qc"
    qc.mkdir(parents=True, exist_ok=True)
    paths = {"summary": qc / "f6_summary.csv"}
    summary(combined).to_csv(paths["summary"], index=False)

    cells = gpd.read_file(path, layer="cells")[["cell_id", "geometry"]]
    base = cells.merge(combined[combined["scenario_id"] == db.BASE_SCENARIO], on="cell_id")
    for column, label, name in (
        ("net_ha_tco2_per_ha_yr", "Net removal, t CO2/ha/yr (medium grain, 10 yr)", "f6_net_ha"),
        ("margin_km", "Break-even distance minus road distance, km", "f6_margin_km"),
    ):
        fig, ax = plt.subplots(figsize=(9, 6))
        base[base["candidate"] == 0].plot(ax=ax, color="#EEEEEE")
        cand = base[base["candidate"] == 1]
        # Colour range from non-ultramafic cells (ultramafic sources would wash out the rest).
        ref = cand.loc[cand["rock_class"] != "ultramafic", column]
        ref = ref if ref.notna().any() else cand[column]
        limit = float(np.nanpercentile(np.abs(ref), 95)) or 1.0
        cand.plot(
            ax=ax,
            column=column,
            cmap="RdBu",
            vmin=-limit,
            vmax=limit,
            legend=True,
            legend_kwds={"label": label, "shrink": 0.6},
        )
        ax.set_title(f"QC — F6 {label}; grey = not candidate — internal", fontsize=9)
        ax.set_axis_off()
        paths[name] = qc / f"{name}.png"
        fig.savefig(paths[name], dpi=130, bbox_inches="tight")
        plt.close(fig)
    return paths
