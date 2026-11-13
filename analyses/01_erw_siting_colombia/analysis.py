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
from mrv_lab.erw_siting import (
    agricultural_frontier,
    land_cover,
    protected_areas,
    regions,
    soil,
    terrain,
)

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
# ### F1 — Soil (SoilGrids 2.0)
# ISRIC SoilGrids 2.0, 250 m (CC BY 4.0; SOURCES.md D8): pH, CEC, clay, SOC, bulk density;
# 0-30 cm thickness-weighted mean of 0-5/5-15/15-30 cm; mean, Q0.05, Q0.95. Model predictions.

# %%
soil_raw = soil.fetch_soilgrids(pilot)
soil_grids = soil.process_soil(soil_raw, pilot)
soil_qc_pngs, soil_qc_csv = soil.save_soil_qc(soil_grids, pilot)

# %% [markdown]
# ### F1 — Current land cover (MapBiomas Colombia, Collection 3.0, 2024)
# CC BY 4.0 (SOURCES.md D6). Agricultural use = classes 21 (mosaic of agriculture and pasture),
# 35 (palm oil), 74 (banana); every pixel keeps its class code. Nearest-neighbour reprojection.

# %%
land_cover_grids = land_cover.clip_land_cover(land_cover.fetch_land_cover(), pilot)
land_cover_qc_png, land_cover_qc_csv = land_cover.save_land_cover_qc(land_cover_grids)

# %% [markdown]
# ### F1 — Slope (Copernicus DEM GLO-30)
# Licence notice: produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence
# and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights
# reserved. Slope kept continuous; threshold chosen in F5 (D-35).
# Optional DEM smoothing (D-36): None = raw 30 m slope; e.g. 5 = 5x5 mean filter (~150 m).

# %%
SLOPE_SMOOTHING_PX: int | None = None
dem_tiles = terrain.fetch_dem(pilot)
slope_grids = terrain.slope_by_department(dem_tiles, pilot, smoothing_px=SLOPE_SMOOTHING_PX)
slope_label = f"_smooth{SLOPE_SMOOTHING_PX}" if SLOPE_SMOOTHING_PX else ""
slope_qc_png, slope_qc_csv = terrain.save_slope_qc(slope_grids, label=slope_label)

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
    print(f"Soil: {len(soil_raw)} raw layers, {len(soil_grids)} processed grids")
    print(f"QC table: {soil_qc_csv.relative_to(root)}")
    lc_table = land_cover.land_cover_summary(land_cover_grids)
    agro_ha = lc_table[lc_table["agricultural_use"]].groupby("department")["area_ha"].sum()
    for name, ha in agro_ha.items():
        print(f"{name}: ~{ha:,.0f} ha agricultural use in {land_cover.YEAR} (QC only)")
    print(f"QC map: {land_cover_qc_png.relative_to(root)}")
    print(f"Slope ({len(dem_tiles)} DEM tiles, smoothing={SLOPE_SMOOTHING_PX}):")
    print(f"QC map: {slope_qc_png.relative_to(root)}")
    print(f"QC table: {slope_qc_csv.relative_to(root)}")
