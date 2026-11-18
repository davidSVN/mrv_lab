"""F7 part A: Monte Carlo of net removal per cell, and one-at-a-time sensitivity (tornado).

Decisions (David, 2026-11-18, D-60):
- 1,000 draws, fixed seed (recorded in ``runs.seed`` and in the draws file).
- Every registry parameter with a source range is drawn from a triangular distribution
  (min, base value, max); the same draw applies to every cell (parameter uncertainty is shared,
  not cell by cell). Fixed: definitions (grain P80, reference temperature, pH threshold) and the
  choices tested as scenarios (application rate, horizon).
- Rock chemistry: whole samples are resampled (Kerr 2002 basalts for basalt and gabbro, García-
  Casco 2020 for ultramafic), keeping each sample's oxides together (D-49). A blank oxide in a
  sample (not analysed) takes the set median.
- Per cell, the draws of net removal (t CO2/t rock, float32) are kept in
  ``data/interim/erw_siting/monte_carlo/<run_id>.npz``; ``cell_results`` gets P5 / P50 / P95 of net
  removal per ha and year and P(net > 0).
"""

from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from mrv_lab import io  # noqa: E402
from mrv_lab.erw_siting import database as db  # noqa: E402
from mrv_lab.erw_siting import history  # noqa: E402
from mrv_lab.erw_siting import net_removal as nr  # noqa: E402

SEED = 20261118
N_DRAWS = 1000
#: Choices tested as scenarios (F7 part B), not drawn.
SCENARIO_CHOICES = frozenset({"application_rate_t_per_ha", "horizon_years"})
OXIDE_SETS = {"basalt": "basalt", "gabbro": "basalt", "ultramafic": "ultramafic"}


def mc_dir() -> Path:
    """``data/interim/erw_siting/monte_carlo/`` (gitignored)."""
    return io.interim_dir() / "erw_siting" / "monte_carlo"


def _is_oxide(pid: str) -> bool:
    return "_wt_pct_" in pid


def uncertain_parameters(table: pd.DataFrame) -> pd.DataFrame:
    """Registry rows drawn in the Monte Carlo: ``ok``, a range with min < max, not a definition,
    not rock chemistry (resampled by sample) and not a scenario choice."""
    rows = []
    for p in table.to_dict("records"):
        rng = p.get("range")
        if p["status"] != "ok" or rng is None or not rng[0] < rng[1]:
            continue
        if p.get("quality") == "definition" or _is_oxide(p["id"]) or p["id"] in SCENARIO_CHOICES:
            continue
        rows.append({"id": p["id"], "low": rng[0], "mode": p["value"], "high": rng[1]})
    return pd.DataFrame(rows, columns=["id", "low", "mode", "high"])


def draw_parameters(table: pd.DataFrame, n: int, rng: np.random.Generator) -> pd.DataFrame:
    """``n`` triangular draws (min, base value, max) of every uncertain parameter."""
    params = uncertain_parameters(table)
    return pd.DataFrame(
        {
            r.id: rng.triangular(r.low, min(max(r.mode, r.low), r.high), r.high, size=n)
            for r in params.itertuples()
        }
    )


def draw_rock(
    sample_sets: dict[str, pd.DataFrame], n: int, rng: np.random.Generator
) -> pd.DataFrame:
    """Whole-sample bootstrap of rock chemistry; columns ``<oxide>_wt_pct_<rock class>``."""
    out = {}
    picks = {}
    for set_name in set(OXIDE_SETS.values()):
        samples = sample_sets[set_name][list(nr.OXIDES)]
        samples = samples.fillna(samples.median())
        picks[set_name] = samples.iloc[rng.integers(0, len(samples), size=n)].reset_index(drop=True)
    for rock, set_name in OXIDE_SETS.items():
        for ox in nr.OXIDES:
            out[f"{ox.lower()}_wt_pct_{rock}"] = picks[set_name][ox].to_numpy()
    return pd.DataFrame(out)


def simulate(
    frame: pd.DataFrame,
    base_values: dict[str, float],
    params: pd.DataFrame,
    rock: pd.DataFrame,
    grain: str,
) -> tuple[np.ndarray, np.ndarray]:
    """Net removal (t CO2/t rock) of every candidate cell for every draw.

    Returns the candidate ``cell_id`` array and a float32 matrix (cells x draws).
    """
    cand = frame[frame["candidate"] == 1]
    rock_class = cand["rock_class"].to_numpy(dtype=object)
    temp = cand["t2m_mean_c"].to_numpy(dtype="float64")
    ph = cand["phh2o"].to_numpy(dtype="float64")
    road = cand["road_km"].to_numpy(dtype="float64")
    n = len(params) if len(params.columns) else len(rock)
    net = np.empty((len(cand), n), dtype="float32")
    for i in range(n):
        values = {**base_values, **params.iloc[i].to_dict(), **rock.iloc[i].to_dict()}
        net[:, i] = nr.chain(rock_class, temp, ph, road, values, grain)["net_tco2_per_t"]
    return cand["cell_id"].to_numpy(), net


def summarise(net: np.ndarray, rate_t_per_ha: float, horizon_years: float) -> pd.DataFrame:
    """P5 / P50 / P95 of net removal per ha and year, and P(net > 0), per cell."""
    q = np.nanpercentile(net, [5, 50, 95], axis=1) * rate_t_per_ha / horizon_years
    valid = ~np.isnan(net)
    p_pos = np.where(valid.any(axis=1), (net > 0).sum(axis=1) / valid.sum(axis=1).clip(1), np.nan)
    return pd.DataFrame(
        {
            "net_ha_p5_tco2_per_ha_yr": q[0],
            "net_ha_p50_tco2_per_ha_yr": q[1],
            "net_ha_p95_tco2_per_ha_yr": q[2],
            "p_net_positive": p_pos,
        }
    )


def store_summary(path: Path, run_id: str, cell_ids: np.ndarray, stats: pd.DataFrame) -> None:
    """Write the Monte Carlo columns of ``cell_results`` for one run."""
    cols = list(stats.columns)
    rows = [
        (*(None if np.isnan(x) else float(x) for x in vals), run_id, cid)
        for cid, vals in zip(cell_ids, stats.to_numpy(), strict=True)
    ]
    with db.connect(path) as con:
        con.executemany(
            f"UPDATE cell_results SET {', '.join(f'{c} = ?' for c in cols)} "
            "WHERE run_id = ? AND cell_id = ?",
            rows,
        )
        con.execute("UPDATE runs SET seed = ? WHERE run_id = ?", (SEED, run_id))


def tornado(
    frame: pd.DataFrame,
    base_values: dict[str, float],
    table: pd.DataFrame,
    grain: str = "medium",
) -> pd.DataFrame:
    """Median net removal (t CO2/t rock) per department with each parameter at its low and high
    end, the others at base (one at a time). Rock oxides use their registry range."""
    cand = frame[frame["candidate"] == 1]
    args = (
        cand["rock_class"].to_numpy(dtype=object),
        cand["t2m_mean_c"].to_numpy(dtype="float64"),
        cand["phh2o"].to_numpy(dtype="float64"),
        cand["road_km"].to_numpy(dtype="float64"),
    )
    dept = cand["department"].to_numpy()

    def medians(values: dict[str, float]) -> pd.Series:
        net = nr.chain(*args, values, grain)["net_tco2_per_t"]
        return pd.Series(net).groupby(dept).median()

    base = medians(base_values)
    rows = []

    def varied(p: dict) -> bool:
        if p["status"] != "ok" or p.get("range") is None or not p["range"][0] < p["range"][1]:
            return False
        if p.get("quality") == "definition" or p["id"] in SCENARIO_CHOICES:
            return False
        # only the grinding energy of the grain being run
        return not p["id"].startswith("grinding_kwh_per_t_") or p["id"].endswith(grain)

    ranged = [p for p in table.to_dict("records") if varied(p)]
    for p in ranged:
        low = medians({**base_values, p["id"]: p["range"][0]})
        high = medians({**base_values, p["id"]: p["range"][1]})
        for d in base.index:
            rows.append(
                {
                    "department": d,
                    "parameter": p["id"],
                    "base": base[d],
                    "at_low": low[d],
                    "at_high": high[d],
                    "swing": abs(high[d] - low[d]),
                }
            )
    return pd.DataFrame(rows).sort_values(["department", "swing"], ascending=[True, False])


def save_tornado_figure(table: pd.DataFrame, out: Path, top: int = 10) -> Path:
    """One panel per department: the ``top`` parameters by swing (internal QC)."""
    depts = list(table["department"].unique())
    fig, axes = plt.subplots(1, len(depts), figsize=(5 * len(depts), 4.5), squeeze=False)
    for ax, d in zip(axes[0], depts, strict=True):
        t = table[table["department"] == d].head(top).iloc[::-1]
        base = t["base"].iloc[0] * 1000
        lo, hi = t["at_low"] * 1000, t["at_high"] * 1000
        ax.barh(t["parameter"], lo - base, left=base, color="#0072B2", label="at low end")
        ax.barh(t["parameter"], hi - base, left=base, color="#D55E00", label="at high end")
        ax.axvline(base, color="black", linewidth=0.8)
        ax.axvline(0, color="grey", linewidth=0.6, linestyle="--")
        ax.set_title(d, fontsize=10)
        ax.set_xlabel("Median net removal, kg CO2 per t rock")
        ax.tick_params(axis="y", labelsize=7)
    axes[0][0].legend(frameon=False, fontsize=8)
    fig.suptitle("QC — tornado: one parameter at a time, medium grain — internal", fontsize=10)
    fig.tight_layout()
    fig.savefig(out, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return out


def run(
    sample_sets: dict[str, pd.DataFrame],
    table: pd.DataFrame,
    path: Path | None = None,
    n: int = N_DRAWS,
) -> dict[str, Path]:
    """Monte Carlo for every F6 grain run, tornado for the base run; internal outputs."""
    path = path or db.database_path()
    frame = nr.load_inputs(path)
    out_dir = mc_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    qc = io.interim_dir() / "erw_siting" / "qc"
    qc.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    summaries = []
    for scenario_id, grain in nr.GRAIN_SCENARIOS.items():
        run_id = f"f6_{scenario_id}"
        base_values = db.scenario_values(scenario_id, path).set_index("parameter_id")["value"]
        base_values = {k: float(x) for k, x in base_values.dropna().items()}
        rng = np.random.default_rng(SEED)  # same draws for every grain run
        params = draw_parameters(table, n, rng)
        rock = draw_rock(sample_sets, n, rng)
        cell_ids, net = simulate(frame, base_values, params, rock, grain)
        stats = summarise(
            net, base_values["application_rate_t_per_ha"], base_values["horizon_years"]
        )
        store_summary(path, run_id, cell_ids, stats)
        paths[run_id] = out_dir / f"{run_id}.npz"
        np.savez_compressed(
            paths[run_id],
            cell_id=cell_ids,
            net_tco2_per_t=net,
            seed=SEED,
            parameter_draws=params.to_numpy(),
            parameter_names=np.array(params.columns),
            rock_draws=rock.to_numpy(),
            rock_names=np.array(rock.columns),
        )
        dept = frame.set_index("cell_id").loc[cell_ids, "department"].to_numpy()
        s = stats.assign(department=dept, scenario_id=scenario_id)
        summaries.append(
            s.groupby(["scenario_id", "department"]).agg(
                cells=("p_net_positive", "size"),
                share_p_net_pos_ge_90=("p_net_positive", lambda x: float((x >= 0.9).mean())),
                share_p_net_pos_le_10=("p_net_positive", lambda x: float((x <= 0.1).mean())),
                median_p_net_positive=("p_net_positive", "median"),
                median_p5=("net_ha_p5_tco2_per_ha_yr", "median"),
                median_p50=("net_ha_p50_tco2_per_ha_yr", "median"),
                median_p95=("net_ha_p95_tco2_per_ha_yr", "median"),
            )
        )
    paths["f7_mc_summary"] = qc / "f7_mc_summary.csv"
    pd.concat(summaries).round(4).reset_index().to_csv(paths["f7_mc_summary"], index=False)

    base_values = db.scenario_values(db.BASE_SCENARIO, path).set_index("parameter_id")["value"]
    base_values = {k: float(x) for k, x in base_values.dropna().items()}
    torn = tornado(frame, base_values, table)
    paths["f7_tornado"] = qc / "f7_tornado.csv"
    torn.round(6).to_csv(paths["f7_tornado"], index=False)
    paths["f7_tornado_png"] = save_tornado_figure(torn, qc / "f7_tornado.png")
    history.snapshot([paths["f7_mc_summary"], paths["f7_tornado"]])
    return paths
