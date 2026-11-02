# Plan — Virtual ERW Field (Colombia) · mrv-lab

Status: draft v0.2 (3D-first order) · 2026-11-02 · Owner: David
Location in repo: `docs/plans/erw_virtual_field.md`
Code targets: `src/mrv_lab/erw/` · `analyses/06_virtual_erw_field/` · `viz/` · `config/`

Reference: Isometric, *Model Quantification for Enhanced Weathering* module v1.0
(https://registry.isometric.com/module/model-quantification-enhanced-weathering/1.0). Section numbers below refer to it.

---

## 0. Goal and framing

Build, fully in code, a **virtual 5,000 ha enhanced rock weathering (ERW) project** in a tropical Colombian setting, and run it through the module's quantification and monitoring requirements wherever they can be verified in a virtual setting.

Outputs:
1. **Virtual field.** Real public soil, climate and topography data, shown in a 3D viewer.
2. **Parameter registry.** Every parameter with value, unit, range, distribution, source (DOI/URL), and its fixed or calibrated status.
3. **Baseline soil model (no rock).** Water, soil CO₂, porewater chemistry, cation exchange, nitrogen, crop uptake.
4. **ERW model.** Feedstock dissolution → Eq. 2 terms → CO₂e exported/stored over 2 simulated years.
5. **MRV layer.**
   - Sampling design
   - Synthetic measurements
   - Tracer mass balance vs. model truth
   - Calibration
   - Global sensitivity (Morris → Sobol)
   - Monte Carlo uncertainty
   - Area of applicability
   - LCA
   - Net CDR

**Mandatory framing (README, figures, posts):** this is a virtual project. Inputs come from public datasets and peer-reviewed literature. There is no field validation, so the validation in §8 is reproduced with synthetic observations and does not count as real validation. Virtual CDR numbers are never presented as estimates for a real project.

---

## 1. Scenario defaults (`config/scenario.yaml` — every item swappable)

| Item | Default | Why |
|---|---|---|
| Region | Altillanura, Meta (Puerto López – Puerto Gaitán) | Flat, homogeneous Oxisols, large contiguous farms, Brazilian Cerrado literature as analog |
| Area | 5,000 ha contiguous cropland | User choice |
| Crop | Maize–soybean rotation, rain-fed, one main rainy-season crop/yr (calendar from literature) | Annual, no flooding (avoid rice), N fertilizer on maize drives the non-carbonic acid term |
| BAU practice | Dolomitic lime + NPK per literature | The BAU control must include liming (unamended controls need 10 yr of liming records, §4.1) |
| Feedstock | Tholeiitic basalt, per-phase mineralogy from a published XRD | Standard ERW rock, moderate rate, low metals |
| Application | Rate and PSD from literature; sensitivity range 10–50 t/ha | — |
| Horizon | 1 yr spin-up + 2 yr simulated, daily forcing (historical years, e.g. 2023–2025) | ≥12 months of continuous forcing (§5.2) |
| Depth | Near-field zone 0–20 cm (module default); model domain 0–100 cm for drainage + viz | §5.2 |

---

## 2. Architecture

```
config/
  scenario.yaml
  parameters/            # registry YAMLs (soil, hydraulics, minerals, exchange, crop, fertilizer, feedstock, lca)
src/mrv_lab/erw/
  data/                  # soilgrids.py, climate.py, dem.py, landcover.py, et.py
  registry.py            # pydantic schema, loaders, validation, units (pint)
  field.py               # field polygon, soil units, columns, random fields
  hydrology.py           # FAO-56 ETa, 1D Richards, water budget
  transport.py           # 1D advection–dispersion (finite volume), Péclet/Courant checks
  geochem.py             # IPhreeqc wrapper: kinetics, exchange, equilibrium, gas
  soil_co2.py            # respiration + diffusion → pCO2 profile
  nitrogen.py            # fertilizer, nitrification, H+ production
  crop.py                # growth, cation uptake, harvest export
  feedstock.py           # phases, PSD, surface area, shrinking core, TST rate laws
  accounting.py          # Eq. 1, Eq. 2 terms, mass/charge balance checks
  sampling.py            # monitoring design, synthetic cores, compositing, lab error
  massbalance.py         # immobile-tracer estimation of feedstock + cation loss
  calibration.py         # synthetic-truth calibration, logs
  sensitivity.py         # SALib Morris / Sobol, emulator
  uncertainty.py         # Monte Carlo (LHS) propagation
  applicability.py       # dissimilarity index (Mahalanobis), climate/soil envelopes
  lca.py                 # grinding, transport, spreading emissions
  export.py              # viewer data export
  cli.py                 # Typer CLI: fetch | build-field | baseline | erw | mrv | export | all
analyses/06_virtual_erw_field/
  README.md  run_pipeline.py  results.json  figures/
viz/                     # TypeScript + three.js + Vite → GitHub Pages
docs/
  plans/erw_virtual_field.md
  adr/                   # architecture decision records
  parameters.md          # auto-generated from registry
  module_compliance.md   # requirement → implementation → status
tests/erw/
data/raw (gitignored) · data/interim · data/processed
```

Core data model: `xarray.Dataset`, dims `(unit, depth, time)` for columns and `(y, x, depth)` for the field grid. Storage: Zarr/NetCDF.
New dependencies (ask before adding each): xarray, zarr, netCDF4, rasterio, rioxarray, geopandas, shapely, pyproj, gstools, pint, pydantic, typer, SALib, scikit-learn, joblib, phreeqpython or phreeqpy, rosetta-soil, pyet (optional), emcee (optional).

---

## Phase 0 — Geochemistry engine spike (gate G-A)

Goal: prove the geochemical engine runs locally and in CI before building on it.

1. Install an IPhreeqc Python binding. Try `phreeqpython` first (bundles IPhreeqc), then `phreeqpy` + the system IPhreeqc library. Test on Linux CI and on David's OS.
2. Reproduce one or two examples from the PHREEQC manual: calcite kinetics, and 1D transport with exchange. Assert results match the manual within tolerance.
3. Database: start with `phreeqc.dat`, and evaluate `llnl.dat` for silicate phases. Record name and version (§5.4 requires it).
4. Kinetic parameters: Palandri & Kharaka (2004), USGS Open-File Report 2004-1068 (acid/neutral/base k₂₅, Eₐ, reaction orders).
5. Fallback if IPhreeqc fails: SCEPTER (open-source Fortran ERW model) through a subprocess.

Exit: CI test green + `docs/adr/001-geochem-engine.md`.

---

## Phase 1 — Physical environment (data acquisition)

Every source goes into `data/SOURCES.md` with URL, access date, license, redistribution status and quality before download. Raw data stays gitignored; fetchers are scripts with checksums.

**1.1 Site selection.** Pick a ~5,000 ha contiguous polygon that is:
- cropland (ESA WorldCover 10 m)
- slope < 3% (DEM)
- inside the Oxisol domain (SoilGrids/IGAC)

Output: `field.geojson`. Document the criteria.

**1.2 Topography.** Copernicus DEM GLO-30 → elevation, slope, flow accumulation (pysheds/richdem). Erosion/deposition risk flag (§4.2).

**1.3 Soil (static).**
- SoilGrids 2.0 (ISRIC, 250 m, depths 0–5/5–15/15–30/30–60/60–100/100–200 cm, mean + Q0.05/Q0.95): pH(H₂O), CEC, clay/silt/sand, SOC, bulk density, coarse fragments, total N. Use the quantiles as uncertainty.
- SoilGrids does **not** provide:
  - base saturation
  - exchangeable Ca/Mg/K/Na/Al
  - soil inorganic carbon
  - total S
  - mobile cation totals
  - immobile tracers (Ti, Zr)
  - porewater chemistry

  Take these from the literature on Llanos Oxisols (IGAC, CIAT, Agrosavia, Cerrado analogs). Each goes into the registry with its DOI and `quality: literature`.
- Check whether IGAC's soil survey for Meta (*Estudio general de suelos*) is accessible and what its license allows.

**1.4 Climate forcing (historical, daily, ≥3 yr).**
- ERA5-Land (Copernicus CDS): 2 m T, dewpoint, radiation, wind, precipitation, soil temperature.
- CHIRPS v2 (0.05°, daily): precipitation, cross-checked against ERA5-Land.
- IDEAM stations (DHIME portal) near the site, for bias checks.
- "Live" refresh (Open-Meteo API) is a later option for the viewer only. It never drives the model.

**1.5 Evapotranspiration.**
- ET₀ via FAO-56 Penman–Monteith.
- **Actual ET** via the FAO-56 dual crop coefficient + soil water stress, using the crop calendar (§5.3 requires actual ET, not reference ET).
- Cross-check against MODIS MOD16A2 (500 m, 8-day).

**1.6 Soil hydraulics.** Rosetta pedotransfer (texture + bulk density → van Genuchten θr, θs, α, n, Ks per layer). Risk: Rosetta is trained mostly on temperate soils, and the microaggregation of Oxisols can bias Ks low. Widen the ranges and document it.

**1.7 Discretization.**
- Soil units: k-means on standardized SoilGrids pixels (pH, CEC, clay, SOC, BD) → K units (8–20). Each unit = one representative 1D column.
- "True" heterogeneous field: Gaussian random fields (gstools) at 25 m, with variograms from the literature or SoilGrids residual structure. MRV samples are drawn from this field (Phase 5).

**1.8 Tests.** Completeness, unit parsing, physical ranges, spatial coverage of the polygon, one data card per source.

Exit: `field.zarr` (static properties per cell × depth) + `forcing.nc` (daily) + first static 3D view (Phase 6.1).

---

## Phase 2 — Parameter registry (the "verified database")

**Schema (pydantic):** `id, name, symbol, value, unit, distribution{type, params}, range[min, max], kind: fixed|calibrated, source{type: dataset|paper|default, citation, doi_or_url, locator (page/table)}, applies_to, quality: primary|secondary|literature, status: ok|missing, notes`.

**Groups:**
- soil
- hydraulics
- minerals (k₂₅, Eₐ, orders, reactive surface area ranges per Table 4)
- exchange (selectivity coefficients, pH-dependent CEC)
- soil CO₂ (respiration Q₁₀, moisture function, diffusivity)
- crop (yields, Ca/Mg/K contents of the harvest)
- fertilizer
- feedstock (mineralogy, PSD, BET)
- LCA (emission factors)

**CI tests:**
- every parameter has a source
- units parse
- the value sits inside its range
- calibrated parameters have pre-defined bounds
- no orphans (every registry parameter is used by the model, and every model parameter is in the registry)

**Hard rule:** Claude Code never fills in a value without a citation. Unknown values get `status: missing` and appear in a list.

Auto-generate `docs/parameters.md` (the fixed/calibrated table required by §5.4).

Runs in parallel with Phase 1.

---

## Phase 3 — Baseline soil model, no rock (gate G-B)

Goal: the counterfactual (control) soil state and fluxes over 2 years, per soil unit. This is where the soil CO₂ system lives. Atmospheric CO₂ over the field is not modeled. What is modeled is soil pCO₂ → porewater DIC, alkalinity, pH.

**3.1 Hydrology.**
- 1D Richards equation (finite volume, van Genuchten, adaptive sub-daily steps).
- Top boundary: P − ETa (with runoff when infiltration capacity is exceeded). Bottom boundary: free drainage.
- Water budget closure P = ETa + drainage + runoff + ΔS, error < 1% per year (§5.3).

**3.2 Transport.**
- Advection–dispersion for solutes, using the Richards fluxes.
- Operator splitting: transport step → geochem step.
- Péclet ≤ 2 (≤ 4 with justification) and Courant ≤ 1 (target ≤ 0.7), computed and asserted at every step.
- Grid convergence test (CDR change < 5%) and time-step sensitivity test (§5.2).

**3.3 Geochemistry (IPhreeqc, per cell).**
- Porewater initialized from literature proxies.
- Ion exchange: CEC with pH dependence, exchanger composition summing to the measured CEC, selectivity coefficients fitted to baseline (§5.3).
- Al chemistry (gibbsite/Al-hydroxides; key in Oxisols).
- Gas phase: pCO₂ from 3.4.
- Saturation indices of calcite, aragonite, dolomite, siderite and magnesite tracked at every step.

**3.4 Soil CO₂.** Respiration as a function of T (Q₁₀) and moisture (parameters from literature) + 1D diffusion–production → pCO₂ profile; open-system representation (recommended in §5.6). Optional: a simple SOC model (RothC-like). Not required.

**3.5 Nitrogen.** Fertilizer NH₄⁺/urea → nitrification (2 mol H⁺ per mol NH₄⁺) → acidity. Required for non-carbonic acid weathering (§5.6). BAU lime included.

**3.6 Crop.** Biomass growth over the calendar; Ca/Mg/K uptake scaled to harvested yield (§5.6).

**3.7 Plausibility vs. literature.** pH, base saturation, Al saturation, drainage fraction, soil pCO₂ range for tropical soils. Each check documented with its source.

Exit: 2-yr baseline runs for all units + diagnostic figures.

---

## Phase 4 — ERW model, with rock (gate G-C)

**4.1 Feedstock.**
- Mineral phases from a published basalt XRD (e.g. plagioclase, pyroxene, olivine, glass, accessories), each with its own rate law. No single proxy phase for a polymineralic rock (§5.3).
- PSD → geometric surface area.
- Reactive surface area log-uniform, down to 3 orders of magnitude below BET (Table 4).
- Shrinking-core surface evolution (recommended); optional passivation.

**4.2 Rate law.** Transition-state theory with acid + neutral + base mechanisms, Arrhenius T correction, affinity term (1 − Ω). Implemented as PHREEQC `RATES`/`KINETICS` blocks. Parameters from Palandri & Kharaka (2004).

**4.3 Application.** Rate (t/ha), timing (pre-planting), incorporation depth.

**4.4 Eq. 2 terms (treated − control, per unit, daily):**
- `Weathering`: charge equivalents of cations released by dissolution
- `BiomassLoss`: extra cation uptake into harvest
- `NetNewCarbonate`: precipitation driven by saturation index
- `NetNewSilicate`: secondary phases, e.g. kaolinite/smectite (recommended)
- `NetSorption`: Δ exchangeable cations (expected to be large in acidic, low-CEC soils)
- `NonCarbonicNeut`: neutralization of nitrification H⁺ and exchangeable acidity (Al³⁺, H⁺), expected to be large in Oxisols
- `Export`: alkalinity/DIC flux crossing the 20 cm boundary

**4.5 Closure test.** Weathering = Σ deductions + export, within tolerance. Cation and charge balance asserted.

**4.6 Storage.** CO₂e_stored = CO₂e_export × η_RiverOcean. η is outside this module (River and Ocean Losses module): fixed assumption with source, flagged.

Exit: daily 2-yr series per unit + area-weighted 5,000 ha total + gross → net waterfall.

---

## Phase 5 — MRV layer (gate G-D)

**5.1 Monitoring design (§4).**
- Treatment + control plots, minimum area from Eq. 3 for 5,000 ha. Compute it from the equation; if it is log-linear between 2.5% at 1,000 ha and 1% at 10,000 ha it gives ≈1.45%. Verify against the text.
- Deployment sampling: ≥1 composite per 10 ha (≥500), composites of 10–20 cores.
- ≥10% of monitoring locations get geochemistry (total digestion of mobile cations + tracers, bulk density).
- Rounds: baseline + end of each reporting period.
- Categorical matching (feedstock, cropping system, drainage).

**5.2 Virtual truth → synthetic measurements.**
- True field = model outputs mapped onto the 25 m random field.
- Add uneven spreading of the feedstock.
- Add core-scale variability, compositing, and analytical error (method CVs from the literature).

**5.3 Estimation.** Soil mass balance with immobile tracers (Ti, Zr) → feedstock fraction and cation loss. Compare the estimate with the model truth: bias, CI, coverage.

**5.4 Power analysis.** Samples needed to detect cation loss at a given confidence, as a function of n, field CV, application rate and analytical error. Output: power curves.

**5.5 Calibration (synthetic truth).**
- Pick a hidden "true" parameter set → generate observables (porewater pH, alkalinity, exchangeable cations) → calibrate from priors.
- Test recovery inside the pre-defined bounds.
- Log pre- and post-calibration values, the bounds, and the calibrated-parameters / observations ratio (§5.4).
- Methods: `scipy.optimize.least_squares`; optional Bayesian with emcee.
- Avoid a good fit on one variable at the cost of correlated ones.

**5.6 Global sensitivity.**
- SALib Morris screening → Sobol on the survivors.
- If runtime is too high: a GP or polynomial-chaos emulator, validated on held-out runs (R² and error threshold documented).
- Monte Carlo candidates: total-order index S_T ≥ 0.05 and defensible range > ×3–5 (§5.5).

**5.7 Uncertainty.**
- Monte Carlo (Latin hypercube) over the flagged parameters + measurement error + log K database inconsistencies (§5.5).
- Output: distribution of CO₂e stored.
- Report mean, CI, and the conservative statistic used for crediting. Take it from the protocol text; document the source.

**5.8 Area of applicability (§4.2).**
- Dissimilarity index, Mahalanobis over pH, texture, CEC, base saturation, application rate.
- Threshold = Q75 + 1.5 × IQR of training DI (mean distance to the 3 nearest points), n ≥ 10p.
- Climate envelope: monthly T + cumulative P.
- Map of cells in/out of the area of applicability. Cells outside cannot be credited.

**5.9 LCA.**
- Grinding energy vs. PSD (kWh/t, literature) × Colombian grid emission factor (UPME/XM).
- Truck transport, quarry → farm (km × EF).
- Spreading diesel.
- Net CDR = stored − LCA emissions.

**5.10 Reporting.**
- `results.json`
- a PDD-like report: parameters, calibration logs, sensitivity, synthetic validation statistics
- a public disclosure layout following §10.3

Exit: gross → net waterfall with uncertainty, power curves, area-of-applicability map, net CDR per ha and for 5,000 ha.

---

## Phase 6 — 3D viewer (`viz/`)

Shows every variable; it is not a data source. It reads pipeline outputs only.

**6.1 Static (after Phase 1).** Terrain from the DEM with vertical exaggeration. Soil voxels 0–100 cm by layer. Variable selector (pH, CEC, clay, SOC, BD, Ks, base saturation). Cut planes (x, y, depth). Soil-unit outline. Legend with units + source.

**6.2 Dynamic (after Phases 3–4).**
- Time slider, 2 years daily: θ, pCO₂, pH, alkalinity, Ca/Mg in porewater, exchangeable cations, remaining feedstock, cumulative CO₂e.
- Treatment/control toggle.
- Overlay of sampling points (Phase 5).
- Click a cell → time-series panel.
- Rain and temperature timeline.

**6.3 Stack.**
- Python `export.py` → chunked Float32 binaries per variable/time + JSON manifest.
- Viewer: TypeScript + three.js + Vite, static, deployed to GitHub Pages by Actions.
- Aggregate to 50–100 m cells for display; precompute; LOD.
- PyVista optional for local preview.

---

## Phase 7 — Packaging and reproducibility

- CLI: `uv run mrv-erw all --scenario config/scenario.yaml` (stages cacheable and runnable one by one).
- Pinned `uv.lock`, fixed seeds recorded in `results.json`, checksummed raw downloads.
- CI: fast unit tests + a smoke scenario (1 unit, 30 days). The full run happens locally, with documented runtime.
- `analyses/06_virtual_erw_field/README.md`: Question / Data / Method / Result / Limitations / Reproduce.
- `docs/module_compliance.md`: each module requirement → file/function → status (`met`, `met-virtually`, `not applicable`, `not met` + reason).

---

## Compliance matrix seed

| Module § | Requirement | Phase | Expected status |
|---|---|---|---|
| Eq. 1–2 | Export and its deductions modeled as one consistent system | 4 | met |
| 5.2 | NFZ 20 cm, grid convergence < 5%, time-step test, ≥12 mo forcing | 3 | met |
| 5.3 | TST rate law per phase, acid/neutral/base, peer-reviewed k and Eₐ | 4 | met |
| 5.3 | Advection–dispersion, Pe ≤ 2, Cr ≤ 1 | 3 | met |
| 5.3 | Carbonate SI tracking + precipitation | 3–4 | met |
| 5.3 | Ion exchange: pH-dependent CEC, sums to CEC, fitted selectivity | 3 | met-virtually |
| 5.6 | Non-carbonic acid (nitrification) | 3 | met |
| 5.6 | Plant uptake scaled to yield | 3 | met |
| 5.3 | Actual ET (FAO-56), water budget closure, hydraulic params | 1, 3 | met |
| 5.4 | Fixed/calibrated classification, bounds, logs, ratio | 2, 5 | met-virtually |
| 5.5 | Global SA (Morris → Sobol), MC candidates rule | 5 | met |
| 4.1 | Treatment/control plots, Eq. 3 area, 1 sample/10 ha, 10% geochem | 5 | met-virtually |
| 4.2 | Categorical matching + DI threshold + climate envelope | 5 | met-virtually |
| 8 | Validation against field observations | 5 | not met (synthetic only) |
| 9 | Monte Carlo propagation | 5 | met |
| 10.3 | Public disclosure | 7 | met |

The rest of §6–10 (data-driven/hybrid models, validation metrics) was not fully reviewed in this draft. Phase 0 includes reading the full module text and completing this table.

---

## Order and gates

**Revised 2026-11-02 (David): 3D scenario first.**

`P1 (data) ∥ P2 (registry) → P6.0 (data contract) → P6.1 (3D static + climate) → P0 → P3 → P4 → P6.2 (dynamic layers) → P5 → P7`

### P6.0 — Viewer data contract (before any viewer code)
Define once, so the viewer never gets rewritten when the model arrives:
- `viz/schema/manifest.schema.json`: grid (x, y, depth, CRS, cell size), variables list, and per variable: `id, label, unit, kind: static|forcing|model, dims, dtype, range, colormap, source, status: available|pending`.
- Static variables (Phase 1): elevation, slope, soil unit, pH, CEC, clay/silt/sand, SOC, bulk density, coarse fragments, total N, van Genuchten params, Ks, plus their Q0.05/Q0.95.
- Forcing variables (Phase 1): daily precipitation, temperature, ET0, ETa, radiation, soil temperature. Shown as a timeline + map/time slider.
- Literature-only soil variables (base saturation, exchangeable cations, Ti/Zr): shown with a "literature" badge and uniform/unit-level values, never as if mapped.
- Model variables (Phases 3–5): θ, pCO2, pH, alkalinity, porewater cations, exchangeable cations, feedstock remaining, CO2e terms, sampling points. Declared in the manifest as `status: pending` from day one; the viewer renders them disabled until the pipeline writes them.
- A test validates every exported manifest against the schema.

### P6.1 scope (expanded)
Everything in 6.1 + forcing timeline + time slider for forcing variables + uncertainty toggle (mean / Q0.05 / Q0.95) + source/license panel per variable. Deployed to GitHub Pages.

Gate G-V (before moving on): all `available` variables render with correct units and sources; cut planes work; manifest validates; viewer loads under 5 s on a normal laptop.

| Gate | Pass condition |
|---|---|
| G-A | IPhreeqc runs in CI and reproduces the manual examples |
| G-B | Water budget closure < 1%/yr; Pe/Cr checks pass; grid convergence < 5% |
| G-C | Cation/charge balance closes; gross → net waterfall sums correctly |
| G-D | Synthetic calibration recovers the hidden parameters inside their bounds; tracer estimate CI covers the truth at the nominal rate |

**Priority constraint:** analysis 01 (verified ERW issuances, due 2026-11-15) goes first. Until it ships, only P1, P2, P6.0 and P6.1 of this plan run.

---

## Risks

- IPhreeqc runtime too high for Sobol → emulator (5.6).
- Literature gaps for Oxisol porewater and selectivity coefficients → wider ranges, documented as `missing`/`literature`.
- Rosetta bias for Oxisols (1.6).
- Data licenses (ERA5/Copernicus, SoilGrids, Copernicus DEM, ESA WorldCover, CHIRPS, IDEAM) → verify each in `SOURCES.md` before committing any derived data.
- Over-claiming → the virtual framing in every output.
- Scope creep: viewer-first order means polish can eat the model's time. Rule: after G-V, viewer work is limited to wiring new `model` variables; no visual polish until G-C passes.
