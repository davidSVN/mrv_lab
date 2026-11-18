# Plan — Where does ERW make sense in Colombia? (analysis 01)

Status: v0.5 · Owner: David · Code targets: `src/mrv_lab/erw_siting/` ·
`analyses/01_erw_siting_colombia/` · `config/erw_siting/`

Companion: [`erw_siting_journal.md`](erw_siting_journal.md) explains each step, the decisions and rules
behind it, and its result. This plan says **what we do now**; the journal says **how we got here**.

This document is the specification for analysis 01. Hard rules:
- Never invent values, URLs or licenses.
- Every parameter carries a source. If there is none: `status: missing`.
- Ask before adding each new dependency.

v0.2 changes vs. v0.1 (agreed with David):
1. **Vertical slice first:** run the full chain (F1–F6) on two departments before scaling nationally.
2. **Separate axes:** soil acidity is an *agronomic* co-benefit (lime substitution) but a *carbon* loss
   (alkalinity spent neutralising acidity). The two are reported on separate axes, never summed.
3. **New source D18:** protected areas (needed by the hard filter in §5.5).
4. No CLI framework and no `.ipynb` in v0.1: one jupytext `analysis.py` (repo contract, CLAUDE.md §6).
5. Generic logic (LCA, Monte Carlo) extends the existing `src/mrv_lab/lca.py` and
   `src/mrv_lab/uncertainty.py`; ERW-specific logic lives in `src/mrv_lab/erw_siting/`.

## 0. Status

Legend: ✅ done · 🔄 in progress · ❓ decision pending · ⛔ blocked · ⏳ not started.
Decision IDs (D-xx, with hyphen) and rules (R-xx) are explained in the journal. Data sources are D1–D30
(no hyphen; D21–D30 added in F4, see `data/SOURCES.md`).

| Phase / step | What | Status | Pending / blocker |
|---|---|---|---|
| P0 | Workspace: plan, analysis folder, CLAUDE.md layout | ✅ | — |
| F0a · T0 | Does this map already exist? | ✅ | Verdict PARTIAL: no equivalent for Colombia; closest is a global web tool (ERW Atlas) without LCA or net removal (R03a, D-55). No further search |
| F0b | License rows in `data/SOURCES.md` | ✅ | D1 publication blocked until SGC answers (D-08); D3 dropped (D-09) |
| F1 · step 0 | Download helper with SHA-256 pinning | ✅ | — |
| F1 · step 1 | Pilot departments (clipping mask) | ✅ | — |
| F1 · step 2 | Protected areas (RUNAP, D18) | ✅ | Revisit sustainable-use categories in Valle (D-17; all three departments kept, D-38) |
| F1 · step 3 | Agricultural frontier (UPRA, D4) | ✅ | Frontier type choice deferred to F5 (D-18) |
| F1 · step 4 | Soil (SoilGrids, D8) | ✅ | — |
| F1 · step 5 | Land cover (MapBiomas 2024, D6) | ✅ | Cropland vs pasture not separable (G-09) |
| F1 · step 6a | Slope from Copernicus DEM (D11) | ✅ | Raw default, optional smoothing (D-36); threshold in F5 (D-35) |
| F1 · step 6b | Rainfall + dry months (CHIRPS), temperature + actual evaporation (ERA5-Land) | ✅ | 1991-2020 normals; recent-climate sensitivity (1996-2025) later in F7 |
| F2 | Lithology: all 194 SGC units classified Apta / Mixta / No apta, with rock types | ✅ | Reviewed by David, proposal accepted (D-43); results internal until SGC answers (D-08) |
| F3 | Rock sources (potential, from suitable polygons near roads) | ✅ | 3,130 potential points (D-46) |
| F4 | Parameter registry with sources, incl. exchangeable Al / base saturation (D20) | ✅ | 40/41 ok (+2 serpentinization parameters, D-57), every value checked against its source by code (D-49, D-51–D-54); exchangeable Al stays missing and unused (G-02). Rock, emissions, weathering approved by David; capture, application, soil decided on sources at his request |
| F5a | Data model and storage: cell tables with every variable (D-24) | ✅ | 12-table GeoPackage: 9 cell/rock/run tables (D-44, D-45) + parameters / scenarios / scenario_parameters (D-50) |
| F5 | Grid, masks, routing | ✅ | 132,264 cells; route validation source still missing (D-47) |
| F6 | Deterministic calculation, three pilot departments | 🔄 | Code + first run done (D-56): 3 grain runs in `cell_results`; checkpoint passed (net > 0 in part of every department). Results internal until SGC answers (D-08). Pending David's review |
| F1–F6 national | Scale to the country | ⏳ | — |
| F7 | Monte Carlo + sensitivity | 🔄 | First run done 2026-11-18 (D-60; ~90 s): per-cell draws in npz (~230 MB), P5/P50/P95 and P(net > 0) in `cell_results`, tornado, 5 assumption scenarios. Results internal (D-08). Pending David's review. Second round: recent climate, Rinder fine grinding (verify first), no-ultramafic scenario |
| F8 | Report | ⏳ | Official municipal boundaries (DANE unreachable, D-11) |
| F9 | Migration to PostgreSQL + PostGIS (same schema, `ogr2ogr`) | ⏳ | Triggered by a dashboard / web app, several writers or national scale (D-44) |
| R09 health research | Health risk per rock unit: asbestos, silica, metals, law, protocols, lab tests (David, separate chat) | ⏳ | Columns ready, all `pending` (D-61); levels assigned only with sourced criteria |
| Study guide | Spanish study guide of every chemical / technical term and formula, with worked examples from this analysis (private page) | ⏳ | Requested by David 2026-11-16; term backlog in the journal; delivered at the end |
| F10 | Scenario dashboard: every variable as a filter or parameter (D-58); compare scenarios; 3D view of Monte Carlo results per cell (exploration only, not for publication) | ⏳ | After F7, on PostGIS (F9); uses `scenarios` (incl. `filters_json`); routes precomputed per rock type; only `base` is citable (D-50) |

Next action: David reviews F6 and F7 results (internal QC in `data/interim/erw_siting/qc/`); then F8.

**Resume point (2026-11-18).** Read this §0, the journal (section "Resume point") and CLAUDE.md.
Data for F1–F5 is processed and stored in `data/interim/erw_siting/erw_siting.gpkg` (gitignored);
`uv run python analyses/01_erw_siting_colombia/analysis.py` rebuilds everything from `data/raw/`.
Open items outside the code: SGC written answer (D-08; email sent by David, reported 2026-11-18), route-validation
source (D-47).

Future (not scheduled, far from now):
- Consolidate all layers into a well-structured spatial database with polygon/cell tables (D-19).
- Processing cache (D-20): today every run re-processes all layers from `data/raw/` (no re-download,
  but e.g. dissolving ~35k UPRA polygons takes minutes). Add a cache that skips re-processing a layer
  when its clean output exists and its raw inputs' SHA-256 are unchanged.
- Land-use stability (D-32): require agricultural use to persist over several years (e.g. 2020–2024)
  instead of 2024 only.
- Research question (D-38): how the location of rock sources in each department changes transport
  emissions relative to removal, and how departments compare.
- Land-use purpose (D-59): compare cells by use — cropland only vs pasture / savanna — to assess how
  ERW behaves on land dedicated to food production versus grazing or other rural uses. Needs a
  cropland vs pasture split (MapBiomas class 21 mixes both, G-09) and the `include_grassland`
  filter (D-58). Not in the base analysis.
- Rock catalogue (D-39): select any rock type, with properties from F4, and re-run the analysis.
  Delivered through the scenario dashboard (F10, D-50).
- Slope view switch (D-36): interactive toggle between raw and smoothed slope maps; choose which feeds the filter.
- ENSO / seasonal variability (D-21): El Niño / La Niña effect on rainfall per zone (CHIRPS since 1981
  + NOAA ENSO index) for project-level forecasting and MRV risk. Not needed for long-term screening.

---

## 1. Question

**In which agricultural areas of Colombia would spreading crushed rock remove net CO₂, and where do
transport, grinding and soil losses eat the gain?**

Sub-questions:
1. Where is suitable rock (mafic or ultramafic: basalt, gabbro, basaltic andesite, dunite) near farmland?
2. What is the road distance from each quarry to each agricultural area?
3. What is the **break-even distance**: how many truck-km cancel the removal per tonne of rock?
4. Which areas combine favourable climate (heat and rain), and rock nearby — and, on a separate axis,
   acidic soils that are already limed?
5. How sensitive is the result to assumptions (grain size, dissolved fraction, soil losses)?

## 2. Why it matters (decisions it supports)

- **ERW developers:** where to look for farms and quarries before spending.
- **Farmers / growers' associations:** whether rock could replace part of the lime in their area.
- **Research groups:** where to place a field trial with the highest chance of success.
- **Verification context:** registries require removal to be demonstrated with field measurements.
  This map **certifies nothing**. It is a screening filter that says where measuring is worthwhile.

Hypothesis to test (not a finding): the Llanos have good climate and soils that are already limed, but
are probably far from mafic rock, which concentrates in the Andean cordilleras. If so, transport decides.
Note: their acidic soils may also raise `f_loss` (§5.2), so the carbon case there can be weaker than the
agronomic case.

## 3. Mandatory framing (README, figures, posts)

- This is a **site-screening analysis with public data**, not a credit estimate.
- Tonnes are **adjusted theoretical potential**, with ranges. Never presented as real removal.
- Every figure carries: "Screening estimate from public data. Not a measured or certified removal."
- Novelty is unverified: before publishing, check whether this map already exists (F0, task T0).

---

## 4. Data sources

Rule: each source gets a row in `data/SOURCES.md` (URL, access date, license, redistribution, quality)
**before** download. Raw data goes to `data/raw/` (gitignored). Downloads are scripts with checksums.

| # | Layer | Official source | Use | License | Status |
|---|---|---|---|---|---|
| D1 | Geology (lithological units) | Servicio Geológico Colombiano (SGC): Mapa Geológico de Colombia 2023, 1:1,500,000. https://www2.sgc.gov.co/MGC/Paginas/mgc_1_5M2023.aspx | Mafic/ultramafic polygons | Conflicting (memoir CC BY 4.0 vs. SGC general terms) | ⛔ Internal use only; publish after SGC answers (D-08) |
| D2 | Geology, finer | SGC: Atlas Geológico de Colombia 2023, 1:500,000 (via MIIG) | Refine polygons in candidate zones | Verify | Exists (checked by David) |
| D3 | Mining titles (real quarries) | Agencia Nacional de Minería (ANM): AnnA Minería geoservices | Quarries with valid title for construction material / rock | No license found for polygons | Dropped in v0.1 (D-09) |
| D4 | Agricultural frontier | UPRA, SIPRA (https://sipra.upra.gov.co) | Mask: where agriculture is allowed | CC BY-SA 4.0 (stricter reading, D-10) | ✅ Downloaded (paged REST, pinned) · both types kept (D-18) |
| D5 | Crop suitability | UPRA, SIPRA zonings (maize, soy, oil palm, …) | Weight zones by crop | Verify | Exists (checked by David) |
| D6 | Land cover / use | MapBiomas Colombia, annual GeoTIFF (Collection 3.0, 1985–2024) | Actual current agriculture | CC BY 4.0 | ✅ Downloaded 2024 map (pinned); classes 21/35/74 = agricultural use (D-31) |
| D7 | Land cover (backup) | ESA WorldCover 10 m | Cross-check D6 | Verify | — |
| D8 | Soil | ISRIC SoilGrids 2.0 (250 m): pH, CEC, clay, SOC, bulk density, Q0.05/Q0.95 | Acidity, lime demand, cation retention | CC BY 4.0 | ✅ Downloaded (native VRT windows, pinned), 45 grids |
| D9 | Precipitation | ERA5-Land total precipitation (CHPclim dropped: no licence, D-37) | Annual rainfall, dry months | CC BY 4.0 | 🔄 CDS request queued |
| D10 | Temperature | ERA5-Land (Copernicus CDS), annual mean 2 m | Dissolution-rate factor | Verify | — |
| D19 | Evapotranspiration | ERA5-Land evaporation variable (to confirm) or MODIS MOD16 | Water surplus = rain − ET (§5.2) | Verify | **New in v0.4** (D-22) |
| D20 | Exchangeable Al / base saturation | Literature, IGAC soil studies (not in SoilGrids) | Soil-loss term `f_loss` in acidic soils | Per source | **New in v0.4** (D-23); likely `missing` |
| D11 | Topography | Copernicus DEM GLO-30 | Slope filter | Verify | — |
| D12 | Roads | OpenStreetMap, HOT export on HDX (Geofabrik unreachable) | Rock access, road distance | ODbL 1.0 | ✅ Downloaded (snapshot 2026-11-02) |
| D13 | Official roads (backup) | INVÍAS national road network | Validate OSM primary roads | Verify | — |
| D14 | Diesel emission factor | UPME, FECOC (2016): 10.180 kg CO2/gal | Truck and spreading emissions | Unclear; values quoted | ✅ (D-51) |
| D15 | Grid emission factor | UPME Res. 085/2026: 0.220 kg CO2e/kWh (2024 inventory factor) | Grinding emissions | Official regulation | ✅ (D-51) |
| D16 | Rock chemistry | Kerr et al. 2002 (basalts, SW Colombia) and García-Casco et al. 2020 (Medellín ultramafics) | CaO, MgO, Na₂O, K₂O → capture potential | Unclear; aggregates only | ✅ (D-49) |
| D17 | Admin boundaries | DANE, Marco Geoestadístico Nacional | Aggregate by municipality / department | Use + transform with citation | ⛔ Unreachable from the cloud session (D-11) |
| D17b | Admin boundaries (clipping only) | geoBoundaries COL ADM1 (OSM-derived) | Clip layers to pilot departments | ODbL 1.0 | ✅ Downloaded, pinned (D-11) |
| D18 | Protected areas | RUNAP, Parques Nacionales Naturales (`latest.zip`, linked by PNNC) | Hard exclusion filter | CC BY-SA 4.0 (stricter reading, D-10) | ✅ Downloaded, pinned, mask built |

Sources already verified in the archived prototype (`archive/erw-3d-viewer-v0`, `data/SOURCES.md`,
accessed 2026-11-02): SoilGrids, Copernicus DEM, WorldCover, ERA5-Land, CHIRPS. Re-check before reuse.

Out of scope for v0.1 (future work): individual farm locations (no public data), real freight prices,
inventory of existing crushers.

---

## 5. Method

### 5.1 Calculation chain

For each agricultural cell *i* (1 km grid) and each rock source *j*:

```
Net removal per tonne of rock (t CO2 / t rock):
  net_ij = CDR_gross_i − E_grind − E_transport_ij − E_spread

Per hectare and year (application rate A t/ha):
  net_ha_ij = net_ij × A / T     (T = assumed dissolution horizon, years)

Break-even distance of cell i:
  d*_i = (CDR_gross_i − E_grind − E_spread) / EF_truck_per_t_km
```

Each cell is assigned the source with the highest `net_ij` (normally the nearest by road).

### 5.2 Gross CDR per tonne of rock (`potential.py`)

1. **Theoretical maximum** counted by charges (D-53; Lewis et al. 2021 Eq. 4):
   `R_CO2 = M_CO2/100 × 2η × Σ(wt%_oxide / M_oxide)` for CaO, MgO, Na₂O, K₂O (each releases 2 moles
   of charge per mole of oxide); η = 0.831 mol CO₂ per mole of charge (Renforth & Henderson 2017,
   ocean pathway). Tested against the source's worked figure (1.66 mol CO₂ per mol Ca²⁺). Lewis
   Eq. 5 (0.5ω for alkalis) and its Table 6 values are not reproducible and not used.
2. **Dissolved fraction over the horizon** `f_diss`, computed per cell (D-52):
   `f_diss = min(1, SSA(P80) × WR × M × s/yr × years × Arrhenius(T_cell))` (Strefler et al. 2018,
   Eq. 2; SSA = 69.18·P80^−1.24 m²/g; WR at pH 7 and 25 °C; Eₐ from Palandri & Kharaka 2004).
   - temperature: Arrhenius correction relative to 25 °C (ERA5-Land mean temperature of the cell);
   - water: **no factor** (no sourced function found); dry months (CHIRPS) reported as a flag (D-52);
   - pH: not in the rate (WR at pH 7); soil acidity enters through `f_loss`.
   Lab-based rates with a three-order range: a **relative index**, not a geochemical model.
3. **Soil losses** `f_loss`, two classes by SoilGrids pH (H₂O, 0–30 cm) (D-54):
   pH < 5.5 → 0.68 (range 0.35–0.68); pH ≥ 5.5 → 0.33 (range 0–0.33). From Su et al. 2026 (ES&T,
   soil columns: cation-based CDR overestimated 1.5–3.1×, most in acidic soil) and Bertagni &
   Porporato 2022 (alkalinity captures ~no CO₂ below pH 5; transition 4.5–6.5). CEC and exchangeable
   Al not used (an acidity mass balance is future work, G-02). Flagged as the most uncertain term.
4. `CDR_gross = CDR_max × f_diss × (1 − f_loss)`.

Optional scenario (only with a source): avoided lime emissions where rock replaces agricultural lime.

### 5.3 Emissions (`src/mrv_lab/lca.py`)

- **Grinding:** kWh/t by target grain size (literature) × SIN factor (D15). Scenarios: coarse, medium, fine.
- **Transport:** road distance (D12) × truck factor in kg CO₂/t·km from FECOC (D14) and a literature
  truck efficiency. Empty return trip as an option.
- **Spreading:** diesel per hectare (literature).
- **Optional:** quarrying.

### 5.4 Road distances (`routing.py`)

- Road graph from OSM (D12). One multi-source Dijkstra from all rock sources to cell centroids
  (snapped to the nearest road node) — not one run per quarry.
- Validation against a sample of routes with distances from a documented source (to define in F5;
  without a source, no validation claim).
- **Fallback** if routing is too heavy: straight-line distance × tortuosity factor, calibrated on the
  same sample. The choice is recorded in an ADR.

### 5.5 Filters and indicators (`siting.py`)

Hard filters: inside the agricultural frontier (D4), current agricultural cover (D6), slope below
threshold (D11), outside protected areas (D18).

Indicators per cell, not blended into a black box:
1. `net_ha` (median and 5–95 percentiles) — **carbon axis**;
2. `d*` vs. actual road distance;
3. lime demand (pH < 5.5 from SoilGrids) — **agronomic axis**, reported separately;
4. climate index.

Any composite score must be transparent, with weights in `config/` and a sensitivity analysis on weights.

### 5.6 Uncertainty and sensitivity (`src/mrv_lab/uncertainty.py`)

- Monte Carlo (Latin hypercube, n ≥ 1,000) over: rock chemistry, η, f_diss, Eₐ, f_loss, kWh/t, truck EF,
  tortuosity factor.
- Global parameters are sampled **once per iteration and applied to all cells** (sampling them per cell
  would understate uncertainty).
- Tornado or Sobol indices to see **which assumption dominates**.
- Key output: probability of `net > 0` per cell.

### 5.7 Scales

- **Vertical slice (decided, D-38):** Meta + Tolima + Valle del Cauca, full chain F1–F6. No Andean
  department is dropped: data for all three are already processed.
- Then national 1 km grid inside the agricultural frontier.
- Regional comparison: Llanos (Meta), an Andean valley, and the Caribbean region.

---

## 6. Deliverables

1. National map of the probability of positive net removal.
2. Break-even distance map with rock sources overlaid.
3. Curve: net removal per tonne vs. transport km, per grain-size scenario.
4. Table by department and municipality: hectares with `P(net>0) > 0.8`, median distance to rock,
   lime demand.
5. Sensitivity tornado.
6. `results.json` + derived CSVs (only if licenses allow) + README (Question / Data / Method / Result /
   Limitations / Reproduce).

## 7. Repository layout

```
config/erw_siting/
  scenario.yaml            # region, grid, thresholds, grain scenarios, weights
  parameters/              # registry: rock.yaml, weathering.yaml, soil_losses.yaml, lca.yaml
data/SOURCES.md            # one row per source (D1–D18)
data/raw/  data/interim/   # gitignored
data/processed/            # derived data only where licenses allow
src/mrv_lab/erw_siting/
  regions.py               # ✅ pilot departments (clipping mask)
  geometry.py              # shared polygon repair helpers
  database.py              # ✅ GeoPackage schema: 12 tables, PostGIS-portable (F5a, D-50)
  protected_areas.py       # ✅ RUNAP exclusion mask (step 2)
  agricultural_frontier.py # ✅ UPRA frontier, both types labelled (step 3)
  soil.py                  # ✅ SoilGrids 0-30 cm grids (step 4)
  land_cover.py            # ✅ MapBiomas 2024 classes + agricultural use (step 5)
  registry.py              # ✅ YAML parameter registry + validator (F4)
  rock_chemistry.py        # ✅ rock oxides recomputed from source tables (F4, D-49)
  emission_factors.py      # ✅ lca factors checked against sources, Bond grinding (F4, D-51)
  weathering.py            # ✅ dissolved fraction per cell: Strefler Eq. 2 + Arrhenius (F4, D-52)
  capture.py               # ✅ R_CO2 by charges, eta = 0.831 (F4, D-53)
  soil_losses.py           # ✅ f_loss by pH class (F4, D-54)
  net_removal.py           # 🔄 F6 net removal per cell, 3 grain runs, QC (D-56, D-58)
  monte_carlo.py           # 🔄 F7 Monte Carlo per cell + tornado (D-60)
  sensitivity.py           # 🔄 F7 assumption scenarios 1-5 (D-60)
  literature.py            # ✅ download, pin and check numbers quoted from documents
  lithology.py             # SGC units → mafic / ultramafic / unsuitable
  quarries.py              # ✅ suitable rock near truck roads → potential sources (F3, D-46)
  grid.py                  # ✅ 1 km grid, cell filters and values (F5)
  cells_pipeline.py        # ✅ F5 orchestration + QC
  potential.py             # §5.2
  routing.py               # ✅ road graph + multi-source Dijkstra (F5)
  siting.py                # §5.5
  report.py                # figures, tables, results.json
analyses/01_erw_siting_colombia/
  README.md  analysis.py  results.json  figures/
docs/plans/erw_siting_colombia.md   # this file
docs/plans/erw_siting_journal.md    # steps, decisions, rules, results
docs/adr/                           # decisions (e.g. real routing vs. tortuosity)
tests/erw_siting/
```

Parameter registry schema:
`id, name, value, unit, distribution{type, params}, range[min,max], source{citation, doi_or_url, locator},
quality: primary|secondary|literature, status: ok|missing, notes`.

Candidate dependencies (approve one by one): geopandas, shapely, pyproj, rasterio, rioxarray, xarray,
osmnx or pandana, networkx, pint, pydantic, pyyaml, SALib. Optional: contextily, folium.

One module per data layer (not a `fetch/` folder): each owns fetch → read → clip → save + QC map.
Downloads go through `mrv_lab.io.download_file` (SHA-256 pinned in `data/checksums.json`).

Single command: `uv run python analyses/01_erw_siting_colombia/analysis.py`.

## 8. Phases and exit criteria

Status per phase: see §0.

| Phase | What | Exit criterion |
|---|---|---|
| P0 | Workspace: this plan, folder, CLAUDE.md layout | Committed |
| F0 | T0 novelty search (by David). License rows for D1, D3, D4, D6, D8 (+ D18) | `SOURCES.md` rows with quoted license text |
| F1-mini | Download + clip, Meta + Tolima + Valle del Cauca | Reproducible scripts with checksum; one control figure per layer, reviewed by David |
| F2 ∥ F4 | Lithology classification · parameter registry | Hand-reviewed unit table · registry tests pass, `missing` list in README |
| F3 | Rock sources: suitable rock near roads, flagged as potential (ANM dropped, D-09) | Layer with origin per source |
| F5a | Data model and storage (D-24) | Schema documented; every layer loads into cell tables; queried by SQL |
| F5 | Grid, masks, routing (two departments) | Validation vs. documented route sample |
| F6 | Deterministic calculation (two departments) | Maps + break-even curve; manual sanity check on 3 cells. **Checkpoint:** if net < 0 everywhere, re-plan before scaling |
| F1–F6 national | Scale the same code to the country | Same criteria at national scale |
| F7 | Monte Carlo + sensitivity | `P(net>0)` map + tornado |
| F8 | Report | Full README, figures with screening label, `results.json` |

## 9. Minimum tests

- Registry: every parameter has a source, units parse, value within range, no orphan parameters.
- Geometry: all layers reprojected to one CRS (MAGNA-SIRGAS / Origen Nacional, EPSG:9377, or the one
  documented); areas reconcile with national totals.
- Units: end-to-end test on a synthetic cell with known result.
- Monotonicity: more distance ⇒ less `net`; finer grain ⇒ more grinding emissions.
- CI: fast tests + a smoke scenario (one department, coarse grid).

## 10. Limitations to declare

- The 1:1.5M geological map misses small quarries and within-unit variation.
- Rock chemistry comes from literature, not own sampling.
- `f_diss` and `f_loss` weigh the most and are the least known in the tropics.
- No riverine/ocean losses or permanence modelled; cited as out of scope.
- No monetary costs in v0.1, carbon only.
- The agricultural frontier says where farming is allowed, not where it happens; hence the MapBiomas cross.

## 11. Relation to the archived 3D prototype

- The 3D viewer is no longer a standalone project. If built, it is a visual layer of this map.
- Reused from `archive/erw-3d-viewer-v0`: registry schema, verified `SOURCES.md` rows, SoilGrids /
  climate / DEM download logic.
