"""F8: publication outputs of analysis 01 (decisions D-65, D-66).

- ``results.json``: every number that may be quoted publicly, computed from the cell database
  (schema of CLAUDE.md §6: key, value, unit, description, as_of).
- Figures (CLAUDE.md §8 style, 1080x1350 PNG + SVG): break-even curve, probability map, margin
  map, tornado, scenarios. Each carries the screening label of the plan (§3).
- The Result section of the analysis README is generated from ``results.json`` (between markers),
  so no number in the README is typed by hand.

``PUBLISH`` is the publication switch (D-65): when True, ``results.json`` and the README are
written into the analysis folder; when False, into ``data/interim/erw_siting/report/``.
``PUBLISH_FIGURES`` is separate because David asked earlier not to commit images to GitHub;
until he confirms, figures go to ``data/interim/erw_siting/report/figures/``.
"""

import json
from datetime import date
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

from mrv_lab import io, plotting
from mrv_lab.erw_siting import database as db
from mrv_lab.erw_siting import monte_carlo as mc
from mrv_lab.erw_siting import net_removal as nr
from mrv_lab.erw_siting import registry, sensitivity

PUBLISH = True  # D-65: SGC-derived results published at David's risk
PUBLISH_FIGURES = False  # images in git need David's confirmation (earlier "no images" rule)
SLUG = "01_erw_siting_colombia"
SCREENING_LABEL = "Screening estimate from public data. Not a measured or certified removal."
FIGURE_SOURCE = (
    "SGC geological map 2023, UPRA, RUNAP, MapBiomas, ISRIC SoilGrids, ERA5-Land (C3S), CHIRPS, "
    "Copernicus DEM, © OpenStreetMap contributors; parameters in data/SOURCES.md"
)
ACCESSED = "2026-11-18"  # latest source access; per-source dates in data/SOURCES.md
DEPARTMENTS = {"Meta": "meta", "Tolima": "tolima", "Valle del Cauca": "valle"}
GRAINS = {"base": "medium", "grain_coarse": "coarse", "grain_fine": "fine"}
README_START = "<!-- results:start -->"
README_END = "<!-- results:end -->"


def output_dirs() -> tuple[Path, Path]:
    """(folder for results.json and README, folder for figures) according to the switches."""
    draft = io.interim_dir() / "erw_siting" / "report"
    analysis = io.analysis_dir(SLUG)
    return (analysis if PUBLISH else draft), (
        analysis / "figures" if PUBLISH_FIGURES else draft / "figures"
    )


def load_results(path: Path | None = None) -> pd.DataFrame:
    """Every stored run joined with cell department and area."""
    with db.connect(path or db.database_path()) as con:
        return pd.read_sql(
            "SELECT r.*, ru.scenario_id, c.department, c.area_in_department_km2 "
            "FROM cell_results r JOIN runs ru USING (run_id) JOIN cells c USING (cell_id)",
            con,
        )


def _entry(key: str, value: float, unit: str, description: str, as_of: str) -> dict:
    return {
        "key": key,
        "value": round(float(value), 4),
        "unit": unit,
        "description": description,
        "as_of": as_of,
    }


def results_entries(table: pd.DataFrame, as_of: str | None = None) -> list[dict]:
    """The quotable numbers, per department and scenario."""
    as_of = as_of or date.today().isoformat()
    out = []
    cand = table[table["candidate"] == 1]
    for dept, slug in DEPARTMENTS.items():
        d = cand[cand["department"] == dept]
        base = d[d["scenario_id"] == db.BASE_SCENARIO]
        if base.empty:
            continue
        out += [
            _entry(
                f"candidate_area_km2_{slug}",
                base["area_in_department_km2"].sum(),
                "km2",
                f"Candidate farmland in {dept} (passes the four hard filters, D-56)",
                as_of,
            ),
            _entry(
                f"share_acid_topsoil_{slug}",
                pd.to_numeric(base["lime_demand"]).mean(),
                "fraction",
                f"Share of {dept} candidate cells with topsoil pH < 5.5 (SoilGrids)",
                as_of,
            ),
            _entry(
                f"median_road_km_to_rock_{slug}",
                base["road_km"].median(),
                "km",
                f"Median road distance from {dept} candidate cells to the nearest Apta rock source",
                as_of,
            ),
            _entry(
                f"median_breakeven_km_medium_{slug}",
                base["breakeven_km"].median(),
                "km",
                f"Median truck distance at which transport cancels net removal, {dept}, "
                "medium grain (100 µm), 10 years",
                as_of,
            ),
            _entry(
                f"median_p_net_positive_medium_{slug}",
                base["p_net_positive"].median(),
                "probability",
                f"Median probability of net removal > 0 over 1,000 Monte Carlo draws, {dept}, "
                "medium grain",
                as_of,
            ),
            _entry(
                f"share_cells_p_net_positive_ge_90_medium_{slug}",
                (base["p_net_positive"] >= 0.9).mean(),
                "fraction",
                f"Share of {dept} candidate cells with P(net > 0) >= 0.9, medium grain",
                as_of,
            ),
            _entry(
                f"median_net_tco2_per_ha_yr_p50_medium_{slug}",
                base["net_ha_p50_tco2_per_ha_yr"].median(),
                "t CO2/ha/yr",
                f"Median of the per-cell Monte Carlo P50 net removal, {dept}, 20 t/ha over 10 "
                "years",
                as_of,
            ),
        ]
        for scenario_id, grain in GRAINS.items():
            g = d[d["scenario_id"] == scenario_id]
            out += [
                _entry(
                    f"share_cells_net_positive_{grain}_{slug}",
                    (g["net_tco2_per_t"] > 0).mean(),
                    "fraction",
                    f"Share of {dept} candidate cells with deterministic net removal > 0, {grain} "
                    "grain",
                    as_of,
                ),
                _entry(
                    f"median_net_tco2_per_t_rock_{grain}_{slug}",
                    g["net_tco2_per_t"].median(),
                    "t CO2/t rock",
                    f"Median deterministic net removal per tonne of rock, {dept}, {grain} grain",
                    as_of,
                ),
            ]
        for scenario_id in sorted(s for s in d["scenario_id"].unique() if s.startswith("s")):
            g = d[d["scenario_id"] == scenario_id]
            out.append(
                _entry(
                    f"share_cells_net_positive_{scenario_id}_{slug}",
                    (g["net_tco2_per_t"] > 0).mean(),
                    "fraction",
                    f"Share of {dept} candidate cells with net removal > 0, assumption scenario "
                    f"{scenario_id}",
                    as_of,
                )
            )
    out.append(_entry("monte_carlo_draws", mc.N_DRAWS, "draws", "Draws per Monte Carlo run", as_of))
    out.append(_entry("monte_carlo_seed", mc.SEED, "seed", "Fixed random seed (D-60)", as_of))
    return out


def breakeven_curve(
    values: dict[str, float], temperature_c: float, ph: float, km: np.ndarray
) -> dict[str, np.ndarray]:
    """Net removal (t CO2/t basalt) along ``km`` of trucking, per grain class."""
    n = len(km)
    return {
        grain: nr.chain(
            np.array(["basalt"] * n, dtype=object),
            np.full(n, temperature_c),
            np.full(n, ph),
            km,
            values,
            grain,
        )["net_tco2_per_t"]
        for grain in ("coarse", "medium", "fine")
    }


#: Readable names for figure labels (registry ids stay in results.json and the CSVs).
PARAMETER_LABELS = {
    "log10_wr_basalt_mol_m2_s": "Weathering rate, basalt",
    "log10_wr_ultramafic_mol_m2_s": "Weathering rate, ultramafic",
    "f_loss_acid_soil": "Alkalinity lost to acid soil",
    "f_loss_neutral_soil": "Alkalinity lost to neutral soil",
    "serpentinized_fraction_ultramafic": "Serpentinized share, ultramafic",
    "log10_rate_ratio_serpentine_forsterite": "Serpentine vs olivine rate",
    "truck_l_diesel_per_t_km": "Truck diesel per t·km",
    "empty_return_factor": "Empty return trip",
    "eta_mol_co2_per_mol_charge": "CO2 per mole of charge (eta)",
    "activation_energy_kj_per_mol_basalt": "Activation energy, basalt",
    "activation_energy_kj_per_mol_ultramafic": "Activation energy, ultramafic",
    "grid_ef_kgco2_per_kwh": "Grid emission factor",
}


def parameter_label(pid: str) -> str:
    """Readable label of a registry id (oxides: 'MgO, gabbro')."""
    if pid in PARAMETER_LABELS:
        return PARAMETER_LABELS[pid]
    if "_wt_pct_" in pid:
        oxide, rock = pid.split("_wt_pct_")
        names = {"cao": "CaO", "mgo": "MgO", "na2o": "Na2O", "k2o": "K2O"}
        return f"{names.get(oxide, oxide)}, {rock}"
    return pid.replace("_", " ")


def _new_figure(left: float = 0.13):  # noqa: ANN202
    """Project figure with room at the bottom for the screening label and a 2-line footer."""
    fig, ax = plotting.new_figure()
    fig.subplots_adjust(left=left, right=0.95, top=0.73, bottom=0.2)
    return fig, ax


def _label(fig) -> None:  # noqa: ANN001
    fig.text(0.06, 0.11, SCREENING_LABEL, fontsize=10, style="italic", color="#5F5F5F")


def _finish(fig, name: str, folder: Path) -> Path:  # noqa: ANN001
    _label(fig)
    plotting.add_footer(fig, FIGURE_SOURCE, ACCESSED, wrap_chars=85)
    return plotting.export_figure(fig, name, folder)[0]


def figure_curve(values: dict[str, float], table: pd.DataFrame, folder: Path) -> Path:
    """Net removal per tonne of basalt vs. truck km, per grain, at the pilot's median conditions."""
    base = table[(table["scenario_id"] == db.BASE_SCENARIO) & (table["candidate"] == 1)]
    with db.connect() as con:
        temp = pd.read_sql(
            "SELECT cell_id, value FROM cell_values WHERE variable = 't2m_mean_c'", con
        ).set_index("cell_id")["value"]
    t_med = float(temp.loc[base["cell_id"]].median())
    km = np.linspace(0, 1000, 201)
    acid = breakeven_curve(values, t_med, values["acid_soil_ph_threshold"] - 0.5, km)
    medium_be = float(km[np.argmax(acid["medium"] < 0)]) if (acid["medium"] < 0).any() else 1000
    fig, ax = _new_figure()
    for grain, color in zip(("coarse", "medium", "fine"), plotting.CYCLE, strict=False):
        ax.plot(km, acid[grain] * 1000, color=color, linewidth=2.5, label=f"{grain} grain")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Road distance from quarry to field, km")
    ax.set_ylabel("Net removal, kg CO2 per tonne of basalt")
    ax.legend(frameon=False)
    plotting.add_title(
        fig,
        f"On acid soil, medium-grain basalt stops paying back after about {medium_be:.0f} km of "
        "trucking",
        "Net CO2 removal per tonne of basalt after grinding, transport and spreading; "
        "acid topsoil, "
        f"{t_med:.0f} °C (median of candidate cells), 10 years",
    )
    return _finish(fig, "breakeven_curve", folder)


def _map(table: gpd.GeoDataFrame, column: str, cmap: str, vmin, vmax, label: str):  # noqa: ANN001, ANN202
    fig, ax = _new_figure(left=0.05)
    table[table["candidate"] == 0].plot(ax=ax, color="#DDDDDD", linewidth=0)
    cand = table[table["candidate"] == 1]
    cand.plot(
        ax=ax,
        column=column,
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
        linewidth=0,
        legend=True,
        legend_kwds={"label": label, "shrink": 0.6, "orientation": "horizontal", "pad": 0.02},
    )
    ax.set_axis_off()
    return fig, ax


def figure_probability_map(cells: gpd.GeoDataFrame, table: pd.DataFrame, folder: Path) -> Path:
    """Probability of net removal > 0 per candidate cell (medium grain)."""
    base = table[table["scenario_id"] == db.BASE_SCENARIO]
    gdf = cells.merge(base, on="cell_id")
    share = (
        gdf[gdf["candidate"] == 1]
        .groupby("department")["p_net_positive"]
        .apply(lambda s: (s >= 0.9).mean())
    )
    fig, _ = _map(gdf, "p_net_positive", "cividis", 0, 1, "Probability that net removal > 0")
    plotting.add_title(
        fig,
        f"{share.get('Tolima', 0):.0%} of Tolima's candidate farmland is at least 90% likely to "
        f"remove CO2, against {share.get('Meta', 0):.0%} in Meta",
        "Probability of positive net CO2 removal per 1 km cell, medium grain (100 µm), 10 years, "
        "1,000 Monte Carlo draws; grey = not candidate farmland",
    )
    return _finish(fig, "probability_map", folder)


def figure_margin_map(
    cells: gpd.GeoDataFrame, table: pd.DataFrame, sources: gpd.GeoDataFrame, folder: Path
) -> Path:
    """Break-even distance minus road distance, with Apta rock sources."""
    base = table[table["scenario_id"] == db.BASE_SCENARIO]
    gdf = cells.merge(base, on="cell_id")
    meta = gdf[(gdf["candidate"] == 1) & (gdf["department"] == "Meta")]
    beyond = float((meta["margin_km"] < 0).mean())
    fig, ax = _map(gdf, "margin_km", "PuOr", -400, 400, "Break-even minus road distance, km")
    xmin, ymin, xmax, ymax = cells.total_bounds
    apta = sources[sources["final_class"] == "Apta"].cx[xmin:xmax, ymin:ymax]
    apta.plot(ax=ax, color="black", markersize=1)
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    plotting.add_title(
        fig,
        f"{beyond:.0%} of Meta's candidate farmland lies beyond the break-even distance to rock",
        "Break-even truck distance minus actual road distance per 1 km cell (purple = rock close "
        "enough), medium grain, 10 years; black dots = potential rock sources",
    )
    return _finish(fig, "margin_map", folder)


def figure_tornado(tornado: pd.DataFrame, folder: Path, top: int = 5) -> Path:
    """Top parameters by swing, one block per department."""
    fig, ax = _new_figure(left=0.42)
    rows, labels, y = [], [], 0
    for dept in DEPARTMENTS:
        t = tornado[tornado["department"] == dept].head(top)
        for r in t.itertuples():
            rows.append((y, r.base * 1000, r.at_low * 1000, r.at_high * 1000))
            labels.append(f"{dept.split()[0]} · {parameter_label(r.parameter)}")
            y += 1
        y += 1
    for yy, base, lo, hi in rows:
        ax.barh(yy, lo - base, left=base, color=plotting.OKABE_ITO["blue"])
        ax.barh(yy, hi - base, left=base, color=plotting.OKABE_ITO["vermillion"])
        ax.plot([base, base], [yy - 0.4, yy + 0.4], color="black", linewidth=1)
    ax.set_yticks([r[0] for r in rows], labels, fontsize=8)
    ax.invert_yaxis()
    ax.axvline(0, color="#5F5F5F", linestyle="--", linewidth=0.8)
    ax.set_xlabel("Median net removal, kg CO2 per tonne of rock")
    top_params = tornado.groupby("department").head(1)["parameter"].unique()
    plotting.add_title(
        fig,
        "Two unmeasured inputs drive the result: "
        + " and ".join(parameter_label(p).lower() for p in top_params[:2]),
        "Change in median net removal when one parameter moves to the low (blue) or high (red) end "
        "of its sourced range, others at base; medium grain, 10 years",
    )
    return _finish(fig, "tornado", folder)


def figure_scenarios(table: pd.DataFrame, folder: Path) -> Path:
    """Share of candidate cells with net removal > 0, base and the eight assumption scenarios."""
    cand = table[table["candidate"] == 1]
    order = [db.BASE_SCENARIO] + sorted(
        s for s in cand["scenario_id"].unique() if s.startswith("s")
    )
    share = (
        cand[cand["scenario_id"].isin(order)]
        .assign(pos=lambda d: d["net_tco2_per_t"] > 0)
        .pivot_table(index="scenario_id", columns="department", values="pos", aggfunc="mean")
        .reindex(order)
    )
    fig, ax = _new_figure(left=0.40)
    for (dept, color), marker in zip(
        zip(DEPARTMENTS, plotting.CYCLE, strict=False), ("o", "s", "D"), strict=True
    ):
        ax.scatter(
            share[dept] * 100,
            range(len(order)),
            color=color,
            marker=marker,
            s=60,
            label=dept,
            zorder=3,
        )
    names = (
        {db.BASE_SCENARIO: "Base (medium grain)"}
        | {k: v[0] for k, v in sensitivity.SCENARIOS.items()}
        | {"s7_fine_rinder_grinding": "Fine grain, higher grinding energy"}
    )
    ax.set_yticks(range(len(order)), [names.get(s, s) for s in order], fontsize=9)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("Candidate cells with net removal > 0, %")
    ax.legend(frameon=False, loc="lower left")
    meta_base = share.loc[db.BASE_SCENARIO, "Meta"]
    meta_s5 = (
        share.loc["s5_meta_without_main_unit", "Meta"]
        if "s5_meta_without_main_unit" in share.index
        else np.nan
    )
    plotting.add_title(
        fig,
        f"Without its one main rock unit, Meta's viable farmland falls from {meta_base:.0%} to "
        f"{meta_s5:.0%}",
        "Share of candidate 1 km cells with positive net removal, base and eight assumption "
        "scenarios (medium grain unless stated)",
    )
    return _finish(fig, "scenarios", folder)


def readme_results_block(entries: list[dict]) -> str:
    """Markdown table of the main results, every number from ``results.json``."""
    by_key = {e["key"]: e for e in entries}
    rows = [
        ("Candidate farmland", "candidate_area_km2_{d}", "{:,.0f} km²"),
        ("Acid topsoil (pH < 5.5)", "share_acid_topsoil_{d}", "{:.0%}"),
        ("Median road distance to rock", "median_road_km_to_rock_{d}", "{:.0f} km"),
        ("Cells with net > 0, coarse grain", "share_cells_net_positive_coarse_{d}", "{:.0%}"),
        ("Cells with net > 0, medium grain", "share_cells_net_positive_medium_{d}", "{:.0%}"),
        ("Cells with net > 0, fine grain", "share_cells_net_positive_fine_{d}", "{:.0%}"),
        ("Median P(net > 0), medium", "median_p_net_positive_medium_{d}", "{:.0%}"),
        (
            "Median net removal, medium (P50)",
            "median_net_tco2_per_ha_yr_p50_medium_{d}",
            "{:.3f} t CO₂/ha/yr",
        ),
        ("Median break-even distance, medium", "median_breakeven_km_medium_{d}", "{:,.0f} km"),
    ]
    head = "| | " + " | ".join(DEPARTMENTS) + " |\n|---|" + "---|" * len(DEPARTMENTS) + "\n"
    body = ""
    for label, pattern, fmt in rows:
        cells = []
        for slug in DEPARTMENTS.values():
            e = by_key.get(pattern.format(d=slug))
            cells.append(fmt.format(e["value"]) if e else "—")
        body += f"| {label} | " + " | ".join(cells) + " |\n"
    as_of = entries[0]["as_of"] if entries else ""
    return (
        f"{README_START}\n_Generated from [`results.json`](results.json) (as of {as_of}); "
        f"{SCREENING_LABEL}_\n\n{head}{body}{README_END}"
    )


def update_readme(readme: Path, block: str) -> None:
    """Replace the generated block of the Result section (or append it after the heading)."""
    text = readme.read_text(encoding="utf-8")
    if README_START in text:
        start, end = text.index(README_START), text.index(README_END) + len(README_END)
        text = text[:start] + block + text[end:]
    else:
        text = text.replace("## Result\n", "## Result\n\n" + block + "\n", 1)
    readme.write_text(text, encoding="utf-8")


def run(path: Path | None = None) -> dict[str, Path]:
    """Write results.json, the README Result block and the five figures."""
    path = path or db.database_path()
    out_dir, fig_dir = output_dirs()
    out_dir.mkdir(parents=True, exist_ok=True)
    table = load_results(path)
    entries = results_entries(table)
    paths = {"results": out_dir / "results.json"}
    paths["results"].write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")

    readme_src = io.analysis_dir(SLUG) / "README.md"
    readme = readme_src if PUBLISH else out_dir / "README.md"
    if not PUBLISH:
        readme.write_text(readme_src.read_text(encoding="utf-8"), encoding="utf-8")
    update_readme(readme, readme_results_block(entries))
    paths["readme"] = readme

    values = db.scenario_values(db.BASE_SCENARIO, path).set_index("parameter_id")["value"]
    values = {k: float(x) for k, x in values.dropna().items()}
    cells = gpd.read_file(path, layer="cells")[["cell_id", "geometry"]]
    sources = gpd.read_file(path, layer="rock_sources")
    frame = nr.load_inputs(path)
    tornado = mc.tornado(frame, values, registry.load())
    paths["breakeven_curve"] = figure_curve(values, table, fig_dir)
    paths["probability_map"] = figure_probability_map(cells, table, fig_dir)
    paths["margin_map"] = figure_margin_map(cells, table, sources, fig_dir)
    paths["tornado"] = figure_tornado(tornado, fig_dir)
    paths["scenarios"] = figure_scenarios(table, fig_dir)
    return paths
