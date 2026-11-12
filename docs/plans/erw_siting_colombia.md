# Plan — Where does ERW make sense in Colombia? (analysis 01)

Status: v0.3 · Owner: David · Code targets: `src/mrv_lab/erw_siting/` ·
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
Decision IDs (D-xx) and rules (R-xx) are explained in the journal.

| Phase / step | What | Status | Pending / blocker |
|---|---|---|---|
| P0 | Workspace: plan, analysis folder, CLAUDE.md layout | ✅ | — |
| F0a · T0 | Does this map already exist? | ❓ | David's search; the first research received covered actors, not maps (D-07) |
| F0b | License rows in `data/SOURCES.md` | ✅ | D1 publication blocked until SGC answers (D-08); D3 dropped (D-09) |
| F1 · step 0 | Download helper with SHA-256 pinning | ✅ | — |
| F1 · step 1 | Pilot departments (clipping mask) | ✅ | — |
| F1 · step 2 | Protected areas (RUNAP, D18) | 🔄 | Implemented and run; awaiting David's review of the QC map/table |
| F1 · step 3 | Agricultural frontier (UPRA, D4) | ⏳ | Exact SIPRA download URL to verify |
| F1 · step 4 | Soil (SoilGrids, D8) | ⏳ | New dependency `rasterio` (ask) |
| F1 · step 5 | Land cover (MapBiomas, D6) | ⏳ | — |
| F1 · step 6 | Slope, rainfall, temperature (D11, D9, D10) | ⏳ | Re-verify licenses from the archived prototype |
| F2 | Lithology: suitable rock; choose the Andean department | ⏳ | D1 usable internally; publishing blocked (D-08) |
| F4 | Parameter registry with sources | ⏳ | — |
| F3 | Rock sources (potential, from suitable polygons near roads) | ⏳ | Depends on D1 (D-09) |
| F5 | Grid, masks, routing | ⏳ | Route-validation source to define |
| F6 | Deterministic calculation, two departments | ⏳ | Checkpoint: re-plan if net < 0 everywhere |
| F1–F6 national | Scale to the country | ⏳ | — |
| F7 | Monte Carlo + sensitivity | ⏳ | — |
| F8 | Report | ⏳ | Official municipal boundaries (DANE unreachable, D-11) |

Next action: David reviews the RUNAP QC map and table → close F1 step 2 → explain F1 step 3 (UPRA).

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
| D4 | Agricultural frontier | UPRA, SIPRA (https://sipra.upra.gov.co) | Mask: where agriculture is allowed | CC BY-SA 4.0 (stricter reading, D-10) | ✅ License OK · download ⏳ |
| D5 | Crop suitability | UPRA, SIPRA zonings (maize, soy, oil palm, …) | Weight zones by crop | Verify | Exists (checked by David) |
| D6 | Land cover / use | MapBiomas Colombia, annual GeoTIFF (Collection 3.0, 1985–2024) | Actual current agriculture | CC BY 4.0 | ✅ License OK · download ⏳ |
| D7 | Land cover (backup) | ESA WorldCover 10 m | Cross-check D6 | Verify | — |
| D8 | Soil | ISRIC SoilGrids 2.0 (250 m): pH, CEC, clay, SOC, bulk density, Q0.05/Q0.95 | Acidity, lime demand, cation retention | CC BY 4.0 | ✅ License OK · download ⏳ |
| D9 | Precipitation | CHIRPS v2 | Annual rainfall | Verify | — |
| D10 | Temperature | ERA5-Land (Copernicus CDS), annual mean 2 m | Dissolution-rate factor | Verify | — |
| D11 | Topography | Copernicus DEM GLO-30 | Slope filter | Verify | — |
| D12 | Roads | OpenStreetMap (Geofabrik Colombia extract) | Road distance | ODbL (verify) | — |
| D13 | Official roads (backup) | INVÍAS national road network | Validate OSM primary roads | Verify | — |
| D14 | Diesel emission factor | UPME, FECOC | Truck emissions | Verify | — |
| D15 | Grid emission factor | UPME/XM, SIN emission factor | Grinding emissions | Verify | — |
| D16 | Rock chemistry | Literature (whole-rock analyses of Colombian basalts; SGC geochemistry if published) | CaO, MgO, Na₂O, K₂O → capture potential | Per article | To search |
| D17 | Admin boundaries | DANE, Marco Geoestadístico Nacional | Aggregate by municipality / department | Use + transform with citation | ⛔ Unreachable from the cloud session (D-11) |
| D17b | Admin boundaries (clipping only) | geoBoundaries COL ADM1 (OSM-derived) | Clip layers to pilot departments | ODbL 1.0 | ✅ Downloaded, pinned (D-11) |
| D18 | Protected areas | RUNAP, Parques Nacionales Naturales (`latest.zip`, linked by PNNC) | Hard exclusion filter | CC BY-SA 4.0 (stricter reading, D-10) | ✅ Downloaded, pinned · step 2 under review |

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

1. **Theoretical maximum** from the cation-based capture-potential formula. The exact formula, molar
   masses, unit convention (oxide wt% → requires /100) and η are taken **from the cited source**
   (e.g. Renforth 2012) and tested against a worked example from that source.
2. **Dissolved fraction over the horizon** `f_diss`: literature range by grain size, adjusted by a
   relative climate factor:
   - temperature: Arrhenius correction relative to 25 °C, Eₐ from literature;
   - water: increasing, saturating factor of rainfall or water surplus (rain − ET).
   This is a **relative index**, not a geochemical model. Documented as such.
3. **Soil losses** `f_loss`, function of SoilGrids pH and CEC:
   - in acidic soil, part of the cations neutralises acidity (Al³⁺, H⁺) instead of capturing CO₂;
   - part is retained on the exchange complex.
   Wide range, sourced, flagged as the most uncertain assumption.
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

- **Vertical slice first (decided):** Meta + one Andean department, full chain F1–F6. The Andean
  department (Tolima or Valle del Cauca) is chosen in F2: the one with more suitable rock near farmland
  according to the SGC geological map (D1).
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
  protected_areas.py       # 🔄 RUNAP exclusion mask (step 2, under review)
  registry.py              # parameter schema + loading + unit validation
  lithology.py             # SGC units → mafic / ultramafic / unsuitable
  quarries.py              # suitable polygons near roads → potential rock sources (ANM dropped, D-09)
  grid.py                  # 1 km grid + masks
  potential.py             # §5.2
  routing.py               # §5.4
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
