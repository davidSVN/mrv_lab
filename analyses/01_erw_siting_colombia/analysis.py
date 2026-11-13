# ---
# jupyter:
#   jupytext:
#     formats: py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # 01 — Where does ERW make sense in Colombia?
#
# Skeleton. Spec: docs/plans/erw_siting_colombia.md. Cells are filled phase by phase.
# Runs end-to-end from raw data: `uv run python analyses/01_erw_siting_colombia/analysis.py`.
# Keep this script thin: reusable logic goes to `src/mrv_lab/` with tests.

# %%
from pathlib import Path

from mrv_lab import io
from mrv_lab.erw_siting import agricultural_frontier, protected_areas, regions

ANALYSIS_DIR = Path(__file__).resolve().parent
FIGURES_DIR = ANALYSIS_DIR / "figures"
RESULTS_PATH = ANALYSIS_DIR / "results.json"

SEED = 42  # Fix and record in results.json if anything is random (CLAUDE.md §9).

# %% [markdown]
# ## Load
# Raw files live in `data/raw/` (gitignored). If the license forbids
# redistribution, add a `download.py` next to this script.

# %%
raw_dir = io.raw_dir()

# %% [markdown]
# ### F1 — Pilot departments (clipping mask)
# geoBoundaries COL ADM1 (ODbL, OSM-derived; SOURCES.md D17b), reprojected to EPSG:9377.
# Used only to clip other layers: not official limits, no areas reported from it.

# %%
departments = regions.read_departments(regions.fetch_departments())
pilot = regions.select_pilot_departments(departments)
pilot_gpkg, pilot_qc_png = regions.save_pilot_departments(pilot, departments)

# %% [markdown]
# ### F1 — Protected areas (exclusion mask)
# RUNAP, Parques Nacionales Naturales (CC BY-SA 4.0; SOURCES.md D18). All categories and all
# conditions are excluded; hectares by category are kept in a QC table to judge their weight.

# %%
runap = protected_areas.read_runap(protected_areas.fetch_runap())
protected_pilot = protected_areas.clip_to_pilot(runap, pilot)
protected_mask = protected_areas.exclusion_mask(protected_pilot)
protected_gpkg, protected_qc_png, protected_qc_csv = protected_areas.save_protected_areas(
    protected_pilot, protected_mask, pilot
)

# %% [markdown]
# ### F1 — Agricultural frontier (UPRA)
# UPRA frontier (MADR Res. 261/2018; CC BY-SA 4.0; SOURCES.md D4), paged REST download.
# Both types kept and labelled ("No condicionada" / "Condicionada"); the choice is made in F5.

# %%
frontier = agricultural_frontier.read_frontier(agricultural_frontier.fetch_frontier())
frontier_mask = agricultural_frontier.frontier_mask(frontier)
frontier_gpkg, frontier_qc_png, frontier_qc_csv = agricultural_frontier.save_frontier(
    frontier_mask, pilot
)

# %% [markdown]
# ## Compute
# Units in variable names when ambiguous: `tonnes_tco2e`, `price_usd_per_t`.

# %%

# %% [markdown]
# ## Figure
# Use `mrv_lab.plotting`: `new_figure`, `highlight_colors`, `add_title`,
# `add_footer`, `export_figure(fig, "<name>", FIGURES_DIR)`.

# %%

# %% [markdown]
# ## Results
# Write every publicly quotable number to `results.json`, one entry per number:
# `{"key": "...", "value": 0.0, "unit": "...", "description": "...", "as_of": "YYYY-MM-DD"}`.

# %%
if __name__ == "__main__":
    root = io.repo_root()
    for name, km2 in zip(pilot["name"], regions.area_km2(pilot), strict=True):
        print(f"{name}: ~{km2:,.0f} km2 (QC only, not official)")
    print(f"Pilot layer: {pilot_gpkg.relative_to(root)}")
    print(f"QC map: {pilot_qc_png.relative_to(root)}")
    for _, row in protected_mask.iterrows():
        print(f"{row['department']}: ~{row['area_ha']:,.0f} ha protected (QC only)")
    print(f"Protected areas: {protected_gpkg.relative_to(root)}")
    print(f"QC map: {protected_qc_png.relative_to(root)}")
    print(f"QC table: {protected_qc_csv.relative_to(root)}")
    for _, row in frontier_mask.iterrows():
        print(
            f"{row['department']} | {row['frontier_type']}: "
            f"{row['n_polygons']:,} polygons, ~{row['area_ha']:,.0f} ha (QC only)"
        )
    print(f"Frontier: {frontier_gpkg.relative_to(root)}")
    print(f"QC map: {frontier_qc_png.relative_to(root)}")
    print(f"QC table: {frontier_qc_csv.relative_to(root)}")
