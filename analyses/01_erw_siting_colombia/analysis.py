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
    cells_pipeline,
    climate,
    database,
    land_cover,
    lithology,
    protected_areas,
    quarries,
    regions,
    registry,
    rock_chemistry,
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
# ### F1 — Climate normals 1991-2020
# Rainfall and dry months: CHIRPS v2.0 (public domain, SOURCES.md D9). Temperature and actual
# evaporation: ERA5-Land (CC BY 4.0, D10/D19; CDS token injected by the environment, never stored).

# %%
era5 = climate.fetch_era5land(pilot)
chirps = climate.fetch_chirps(pilot)
climate_grids = climate.process_climate(era5, chirps, pilot)
climate_qc_pngs, climate_qc_csv = climate.save_climate_qc(climate_grids, pilot)

# %% [markdown]
# ### F2 — Lithology (SGC 2023) — internal use only until SGC answers (D-08)
# All 194 units classified Apta / Mixta / No apta; David's review file is merged (D-43).

# %%
geo_units = lithology.read_units(lithology.fetch_geology())
unit_table = lithology.unit_table(geo_units, pilot)
unit_table = lithology.apply_review(
    unit_table, io.interim_dir() / "erw_siting" / "geology" / "lithology_review.csv"
)
classified = lithology.classified_units(geo_units, unit_table)
lithology.save_lithology(classified, unit_table, departments, pilot)

# %% [markdown]
# ### F3 — Potential rock sources (truck roads within 5 km of suitable rock, D-46)

# %%
rock_sources = quarries.potential_sources(
    quarries.read_truck_roads(quarries.fetch_roads()), classified
)
quarries.save_quarries(rock_sources, classified, departments, pilot)

# %% [markdown]
# ### F5 — Cell database (GeoPackage): grid, filters, values and road routing (D-44, D-47)

# %%
database.create_database(overwrite=True)
database.write_rock_tables(unit_table, rock_sources)
f5_qc = cells_pipeline.run(pilot)

# %% [markdown]
# ### F4 — Parameter registry (values filled group by group; missing ones are listed)

# %%
parameters = registry.load()
registry_problems = registry.validate(parameters)
if registry_problems:
    raise ValueError(f"Parameter registry invalid: {registry_problems}")
missing_parameters = registry.missing(parameters)

# %%
# Rock group: recompute every value from the source tables (D-49); fail if the YAML drifted.
rock_texts = {k: rock_chemistry.pdf_text(p) for k, p in rock_chemistry.download().items()}
rock_mismatch = rock_chemistry.check_registry(
    parameters, rock_chemistry.registry_values(rock_texts)
)
if rock_mismatch:
    raise ValueError(f"rock.yaml differs from the sources: {rock_mismatch}")
rock_samples = rock_chemistry.sample_sets(rock_texts)

# %%
# Registry -> GeoPackage: `parameters` (read-only copy) + the citable `base` scenario (D-50).
database.write_parameters(parameters)
print({name: len(s) for name, s in rock_samples.items()})

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
    print(f"Climate QC table: {climate_qc_csv.relative_to(root)}")
    print(f"Lithology: {unit_table['final_class'].value_counts().to_dict()} (internal)")
    print(f"Rock sources: {len(rock_sources)} potential points (internal)")
    print(f"F5 QC: {', '.join(str(v.relative_to(root)) for v in f5_qc.values())}")
    print(f"Parameters: {len(parameters)} ({len(missing_parameters)} missing)")
