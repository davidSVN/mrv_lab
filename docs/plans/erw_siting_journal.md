# Journal — Where does ERW make sense in Colombia? (analysis 01)

Companion to the plan [`erw_siting_colombia.md`](erw_siting_colombia.md). The plan says what we do
now (§0 has the live status). This journal explains, step by step, **what each step is for, what was
decided and why, which working rules came out of it, and what the step produced.**

Conventions:
- Decisions are numbered `D-xx`, working rules `R-xx`. IDs never change; a reversed decision gets a new
  entry that points to the old one.
- Evidence = commit hash on branch `claude/inspiring-shannon-e112ll`, or a row in `data/SOURCES.md`.
- Updated in the same commit as the change it describes.
- Public repo: technical content only.

Status legend: ✅ done · 🔄 in progress · ❓ decision pending · ⛔ blocked · ⏳ not started.

---

## Working rules

| ID | Rule | Why | Since |
|---|---|---|---|
| R-01 | No deadlines. Priorities and dates are set only by David, per conversation. | Avoid invented pressure; David controls pace. | 2026-11-05 |
| R-02 | A URL is shared only after it was opened and responded; otherwise it is labelled "not verified". | Unverified URLs cost David time (several DANE links failed). | 2026-11-12 |
| R-03 | Every download goes through `mrv_lab.io.download_file`: downloaded once, SHA-256 pinned in `data/checksums.json`, error if the file changes. Raw data stays out of git. | A silent change at the source must never change results unnoticed. | 2026-11-10 |
| R-04 | Unclear license ⇒ do not download (CLAUDE.md §7). Exceptions are approved by David and written in `SOURCES.md`. | Legal and reputational safety of a public repo. | 2026-11-10 |
| R-05 | When two official statements of a license conflict, apply the stricter one. | Safe by default; can relax with written confirmation. | 2026-11-10 |
| R-06 | Never strip attribution or publish "anonymised" sources. | Open licenses require attribution; hiding a source does not fix a license problem and destroys traceability. | 2026-11-10 |
| R-07 | QC maps are internal (`data/interim/**/qc/`, gitignored), one per layer, reviewed by David. Publishable figures go through `mrv_lab.plotting`. | Separate checking from communicating. | 2026-11-12 |
| R-08 | Code is explained (inputs, outputs, libraries, how to run) before it is written, and implemented only after David's explicit OK. Mechanical sub-steps run together; stop for review before commit when real data first enters. | David must understand every piece of code. | 2026-11-06 |
| R-09 | If an environment hook forces a commit before review, commit on the working branch only, revertible, never on `main`. | Keep the hook satisfied without bypassing David's review. | 2026-11-12 |
| R-10 | On failure: stop, explain, propose options. No source or method switch without approval. | Avoid silent design changes. | 2026-11-10 |
| R-11 | Each decision updates the plan (if it changes the method) **and** this journal, in the same commit. | One place for "now", one for "why". | 2026-11-12 |

---

## P0 — Workspace ✅

**Purpose.** Separate the new analysis from the archived 3D-viewer prototype and set up its folder.

**Decisions**
- **D-01 (2026-11-05)** — Repository refocused on this analysis. The virtual-field + 3D-viewer work is
  archived in branch `archive/erw-3d-viewer-v0`; `main` holds only the shared base.
  *Alternative rejected:* copying the viewer into an `archive/` folder (50k+ lines of GeoJSON in the
  public repo; git already keeps it). *Evidence:* `main` at `d76f661`, archive branch.
- **D-02 (2026-11-05)** — The old roadmap (analyses 01–06) is removed; this is analysis **01**.
  *Evidence:* `019f6ca`.
- **D-03 (2026-11-06)** — Folder `analyses/01_erw_siting_colombia/`; spec in `docs/plans/`.
  *Evidence:* `2b294c6`.
- **D-04 (2026-11-06)** — Plan v0.2 changes: (1) vertical slice on two departments before national
  scale; (2) carbon and agronomic axes reported separately (acidic soil = lime co-benefit but carbon
  loss); (3) protected areas added as source D18; (4) one jupytext `analysis.py`, no CLI or notebook;
  (5) generic logic in existing `lca.py` / `uncertainty.py`. *Evidence:* `2b294c6`.

**Result.** Skeleton analysis folder, plan in English, `docs/adr/` and `data/interim/` created.

---

## F0a — T0: does this map already exist? ❓

**Purpose.** Before publishing, check whether an ERW siting/suitability map for Colombia already
exists, so novelty is not over-claimed (plan §3).

**Decisions**
- **D-07 (2026-11-10)** — The first research received maps ERW *actors and trials* in Colombia; it does
  not search for *maps or suitability studies*. T0 stays open; a dedicated search prompt was written
  for David to run.

**Useful inputs from that research** (to be sourced properly when used): diabase sold as rock flour in
Valle del Cauca and a 2025 paper on mafic weathering profiles in the Western Cordillera (hint for the
Andean department, to confirm in F2); a conference abstract with trial parameters (low quality:
not peer reviewed, confounded by manure); commercial rock flour is coarse (mesh 20), so grinding
emissions matter.

**Result.** Pending David's search.

---

## F0b — License rows ✅ (with one block)

**Purpose.** No data is downloaded before its license is recorded (R-04).

**Decisions**
- **D-08 (2026-11-10)** — **SGC geological map (D1):** the explanatory memoir says CC BY 4.0, but SGC
  general terms forbid publishing derived data without written permission. Approved exception:
  download and internal use allowed; any derived map, table or number is published only after SGC
  answers in writing. If SGC says no, switch to the most open alternative and declare it.
  *Evidence:* `SOURCES.md` D1, `c861e87`.
- **D-09 (2026-11-10)** — **ANM mining titles (D3) dropped in v0.1:** no license found for the title
  polygons. Rock sources become "potential" (suitable SGC polygons near roads), as the plan's fallback.
  Consequence: rock sources now depend on D1. *Evidence:* `SOURCES.md` D3.
- **D-10 (2026-11-10/12)** — **Stricter reading (R-05):** UPRA's license text says both CC BY 4.0 and
  CC BY-SA 4.0 → treat as BY-SA. RUNAP: datos.gov.co says CC BY 4.0, PNNC's own portal says
  CC BY-SA 4.0 → treat as BY-SA. Derived layers from them carry BY-SA.

**Result.** Licenses recorded with quoted text for D1, D3, D4, D6, D8, D17, D17b, D18.

| Source | License (applied) | Status |
|---|---|---|
| D1 SGC geology | Conflicting | ⛔ publish only after SGC answers |
| D3 ANM titles | Not found | Dropped in v0.1 |
| D4 UPRA frontier | CC BY-SA 4.0 | ✅ |
| D6 MapBiomas | CC BY 4.0 | ✅ |
| D8 SoilGrids | CC BY 4.0 | ✅ |
| D17 DANE MGN | Use + transform with citation | ⛔ unreachable from cloud |
| D17b geoBoundaries | ODbL 1.0 | ✅ |
| D18 RUNAP | CC BY-SA 4.0 | ✅ |

---

## F1 — Data download and clipping (Meta, Tolima, Valle del Cauca) 🔄

**Purpose.** Have every licensed layer on disk, clipped to the pilot departments, pinned by checksum,
with a QC map David reviews.

**Decision**
- **D-05 (2026-11-06/10)** — Pilot = Meta + one Andean department. Both Andean candidates (Tolima,
  Valle del Cauca) are downloaded now; the one with more suitable rock near farmland (SGC map) is
  chosen in F2. *Why Meta:* tests the hypothesis "good climate and limed soils, far from rock".
- **D-06 (2026-11-10)** — One module per layer (`regions.py`, `protected_areas.py`, …) instead of a
  `fetch/` folder: each owns fetch → read → clip → save + QC map.

### Step 0 — Download helper ✅

**What.** `io.download_file(url, dest)` downloads once, records the file's SHA-256 in
`data/checksums.json`, and raises `ChecksumMismatchError` if the file later differs.
**Rule created:** R-03. **Result.** 3 offline tests. *Evidence:* `c861e87`.

### Step 1 — Pilot departments ✅

**What.** `erw_siting/regions.py`: read department boundaries, select the three pilots
(case/accent-insensitive), reproject to EPSG:9377 (MAGNA-SIRGAS / Origen-Nacional, metres), save a
GeoPackage and a QC map.

**Decisions**
- **D-11 (2026-11-10/12)** — Boundaries: DANE (official) is unreachable from the cloud session and its
  geoportal returned HTTP 503 to an independent fetcher; David could not open it either. Use
  **geoBoundaries COL ADM1** (OSM-derived, ODbL) **only as a clipping mask**; no areas are reported
  from it. Official DANE limits remain the target for municipal tables in F8.
- **D-12 (2026-11-12)** — Download geoBoundaries through its direct Git LFS URL
  (`media.githubusercontent.com`, full commit SHA). The `github.com/.../raw/` URL is refused by the
  session's proxy (GitHub access is per repository); same file, same license.
  *Rejected:* HDX/OCHA boundaries (good, DANE-derived, but 117 MB and a 2021 file — kept as fallback).
- **D-13 (2026-11-12)** — `geopandas` added as dependency (brings `shapely`, `pyproj`, `pyogrio`).

**Result.** 33 departments read; Meta, Tolima and Valle del Cauca selected and saved to
`data/interim/erw_siting/pilot_departments.gpkg`; QC map approved by David on 2026-11-12 (labels moved
to margins to stop overlap). Second run reuses the cached file. 14 tests pass.
*Evidence:* `48743bf`, `1be312d`, `e28bef5`.

### Step 2 — Protected areas (RUNAP) ✅

**What.** `erw_siting/protected_areas.py`: download the RUNAP shapefile, keep name / category /
condition, repair invalid polygons (keep polygon parts only), reproject to EPSG:9377, intersect with
the pilot departments (an area crossing a border is split per department), build a per-department
union mask (overlaps counted once), and save a GeoPackage (`areas`, `mask`), a QC map and a QC table
of hectares by department × category × condition.

**Facts verified (2026-11-12).** PNNC's portal links
`https://storage.googleapis.com/pnn_geodatabase/runap/latest.zip` and declares CC BY-SA 4.0. File of
2026-11-06: 70,264,674 bytes, `runap.shp`, EPSG:4686, 1,952 areas, 14 categories (`ap_categor`),
condition field `condicion` (REGISTRADA / INSCRITA / CONSTRUCCION).

**Decisions (David, 2026-11-12)**
- **D-14** — Exclude **all 14 categories**; report hectares per category in the QC table. Some
  sustainable-use categories (integrated-management districts, soil-conservation districts, private
  reserves) may allow production in part of their area; refine only with Decreto 1076 de 2015 as
  source, if their weight justifies it. *Rejected for now:* excluding only strict categories without a
  sourced rule.
- **D-15** — Exclude regardless of **condition** (REGISTRADA, INSCRITA, CONSTRUCCION); counts reported.
  *Why:* the meaning of CONSTRUCCION is not documented here; excluding is the conservative choice.
- **D-16** — **Update policy:** the downloaded `latest.zip` is pinned by SHA-256. When PNNC overwrites
  it, the checksum check fails and the new version is accepted deliberately (delete file + registry
  entry, re-run).

**Result (approved by David, 2026-11-12).** Mask, QC map and QC table written to `data/interim/erw_siting/`
(gitignored). First reading of the QC table: national natural parks dominate the excluded area in
Meta and Tolima; in Valle del Cauca sustainable-use categories weigh more, so D-14 matters most
there. Numbers stay QC-only until they come from `results.json`. 17 tests pass.

- **D-17 (2026-11-12)** — Revisit whether integrated-management and soil-conservation districts
  should be fully excluded **only if Valle del Cauca is chosen in F2**, with Decreto 1076 de 2015 as
  source. If Tolima is chosen, the question has little weight and is left as is.

### Step 3 — Agricultural frontier (UPRA) ✅

**What.** `erw_siting/agricultural_frontier.py`: query the UPRA ArcGIS REST layer per pilot department
(DANE codes 50, 73, 76) in pages of 2,000 polygons ordered by `objectid`, store each page as a file
pinned by SHA-256, merge pages (dropping duplicate `objectid`), repair polygons, reproject to
EPSG:9377, dissolve per department × frontier type, and save a GeoPackage, a QC map and a QC table.
Shared polygon-repair code moved to `erw_siting/geometry.py` (also used by step 2).

**Facts verified (2026-11-13).** Layer "Frontera agrícola y frontera agrícola condicionada"
(MADR Resolución 261 de 2018), 465,583 polygons nationally, two types: *No condicionada* (suitable for
farming by law) and *Condicionada* (farming may be permitted, restricted or prohibited by law).
Repeated requests return byte-identical pages, so per-page checksums are stable. The service does not
declare a version date. Its inputs include RUNAP 2023 and páramo limits.

**Decisions**
- **D-18 (David, 2026-11-13)** — Keep **both frontier types, labelled**; decide in F5 which counts as
  candidate land, with numbers. *Rejected:* only "No condicionada" (may exclude land where farming is
  allowed) and both as equal (may include land where farming is prohibited).
- **D-19 (David, 2026-11-13)** — Future: consolidate the layers into a well-structured spatial
  database with polygon tables. Not scheduled; today each layer is one GeoPackage in `data/interim/`.
- **D-20 (David, 2026-11-13)** — Future, far from now: processing cache. Every run currently
  re-processes all layers from `data/raw/` (no re-download). Skip a layer when its clean output exists
  and its raw inputs' SHA-256 are unchanged. Design together with D-19.

**Result (approved by David, 2026-11-13).** Polygon counts per department match the server counts. Raw pages:
19 files, ~366 MB (gitignored); first run ~5 minutes. Consistency check against the step-2 RUNAP mask:
the frontier barely overlaps protected areas in Meta and Tolima; the overlap is larger in Valle del
Cauca, consistent with sustainable-use districts where UPRA allows farming (links to D-17). Numbers
stay QC-only. 21 tests pass.

### Step 4 — Soil (SoilGrids 2.0) ✅

**What.** `erw_siting/soil.py`: for 5 variables × 3 depths × 3 statistics, read a window around each
pilot department from the native SoilGrids VRT and store it as GeoTIFF (135 files, SHA-256 pinned
through `io.register_checksum`); then per department × variable × statistic: thickness-weighted
0–30 cm mean, conversion to conventional units, reprojection to EPSG:9377 at 250 m (bilinear),
masking to the department outline (45 grids), QC maps (one per variable) and a QC summary table.

**Decisions (David, 2026-11-13)**
- **D-26** — Variables: pH (water), CEC, clay, soil organic carbon, bulk density.
- **D-27** — Depth 0–30 cm = thickness-weighted mean of 0–5, 5–15, 15–30 cm. For Q0.05 / Q0.95 this is
  an approximation (a weighted mean of layer quantiles is not the quantile of the 0–30 cm mean).
- **D-28** — Statistics: mean, Q0.05, Q0.95 (feed uncertainty in F7).
- **D-29 (technical, 2026-11-13)** — Read the **native VRT** (Interrupted Goode Homolosine, explicit
  nodata −32768) instead of the WCS, which returns server-resampled EPSG:4326 with no-data as 0; this
  avoids double resampling. Conversion factors taken from ISRIC's "SoilGrids layers" FAQ.
- **D-30 (technical, 2026-11-13)** — `files.isric.org` reset connections intermittently and stopped the
  first runs at 75/135 layers. Each window read now retries 4 times (5/15/30/60 s) on a fresh handle,
  with GDAL HTTP retries. Rule R-03 unchanged (each file pinned).

**Result (approved by David, 2026-11-13).** 135/135 raw layers, 45 processed grids. Pixel counts match the
QC department areas (250 m pixels). First reading: Meta is the most acidic and has the lowest CEC
(typical of the Llanos Oxisols); the Cauca river valley in Valle del Cauca stands out with the
highest pH. Numbers stay QC-only. 26 tests pass. Model predictions, not measurements (gap G-01).

### Step 5 — Current land cover (MapBiomas Colombia 2024) ✅

**What.** `erw_siting/land_cover.py`: download the official 2024 national map (Collection 3.0, ~30 m,
SHA-256 pinned), read a window per department, reproject to EPSG:9377 at 30 m with **nearest
neighbour** (categorical data), mask to the department outline, and save one class raster per
department, a QC map (agricultural classes highlighted) and a QC table of hectares per class.

**Facts verified (2026-11-13).** File linked from the official download page (Google Drive), 95 MB,
EPSG:4326, uint8. Official legend PDF: agricultural classes are 9 (forest plantation), 35 (palm oil),
74 (banana, beta) and 21 (mosaic of agriculture **and** pasture). There is no separate cropland class.

**Decisions (David, 2026-11-13)**
- **D-31** — Agricultural use = classes **21 + 35 + 74**; forest plantation (9) excluded (trees, not
  annually managed soil). ERW can also be applied on pasture, so the mosaic class is kept. Every pixel
  keeps its class code.
- **D-32** — Year **2024 only**; multi-year stability (e.g. 2020–2024) is future work.

**Result (approved by David, 2026-11-13).** Department totals match the QC areas of step 1. Agricultural use
dominates the Cauca river valley; palm oil appears in northern Meta; no banana pixels in the pilot
departments. Numbers stay QC-only. 29 tests pass.

### Step 6 — Slope and climate (split into 6a and 6b)

**Decisions (David, 2026-11-13)**
- **D-33** — Split step 6: **6a slope** (Copernicus DEM) and **6b climate**, each with its own review.
- **D-34** — Rainfall from **CHPclim v2** (Climate Hazards Center monthly climatology, 12 maps; period
  to verify in its documentation); the 30-year CHIRPS monthly series is kept for ENSO work (D-21).
  Temperature and evapotranspiration: **ERA5-Land** recommended (monthly means, CC BY, "January 1950 to
  present", updated monthly with a 2–3 month delay per its CDS page, checked 2026-11-13). David saw a
  "no longer updated" notice on a Copernicus page; the dataset page shows no such notice (likely the
  legacy CDS retired in 2024 — to confirm with the URL). A long-term average does not need recent
  months anyway. Needs a free CDS account + API key (secure credential form). Alternative without key:
  CHC CHTclim (temperature; variable to verify) and Hobbins RefET (marked "experimental" by CHC).
- **D-35** — Slope kept as a **continuous percentage**; the threshold (8 % or 12 %) is fixed in F5 with
  a cited source. The DEM is a surface model (trees, buildings); forests are removed by land cover.

### Step 6a — Slope (Copernicus DEM GLO-30) 🔄

**What.** `erw_siting/terrain.py`: download the 1°×1° land tiles covering the pilot departments (ocean
tiles do not exist), mosaic per department, reproject to EPSG:9377 at 30 m (bilinear), compute slope
with central differences, mask to the outline, and save a slope GeoTIFF per department, a QC map with
the 8 % / 12 % bands and a QC table with the share of land per band.

**Result (first run, 2026-11-13).** 28 land tiles (1.1 GB), slope for the three departments in ~2 min.
Flat Llanos show speckled "steep" pixels: the DEM is a surface model, so tree and field edges read as
slope. Test window in the Llanos (~30 × 30 km): share > 12 % = 4.7 % raw vs 0.1 % with a 5×5 mean
filter (median 1.16 % vs 0.87 %).

- **D-36 (David, 2026-11-13)** — DEM smoothing is an **option**, not the default: `smoothing_px`
  (None = raw 30 m slope; e.g. 5 = 5×5 mean filter, files suffixed `_smooth5`). Which version feeds the
  filter is decided later; future work: a switch to compare raw vs smoothed maps interactively.

---

## Plan v0.4 — variables review (2026-11-13)

**Purpose.** Check that every variable the method needs has a source, before more downloads.

**Decisions (David, 2026-11-13)**
- **D-21** — El Niño / La Niña and interannual variability: **future work**, not a new step. A 20+ year
  rainfall average already includes ENSO years; ENSO matters for project-level forecasting and MRV
  risk, not for long-term screening. Data exists (CHIRPS since 1981, NOAA ENSO index).
- **D-22** — **Expand F1 step 6**: rainfall (annual total + number of dry months, both from CHIRPS)
  and temperature + evapotranspiration (ERA5-Land). The plan's water term (rain − ET, §5.2) had no ET
  source; new source D19.
- **D-23** — **F4 registry** adds exchangeable aluminium / base saturation (new source D20, literature or
  IGAC). It drives soil losses in acidic soils and is not in SoilGrids; expected to stay `missing` or
  wide-ranged, and is flagged as the weakest assumption.
- **D-24** — **New step F5a: data model and storage.** Store every per-cell variable in structured
  tables instead of loose files. Storage engine (GeoPackage vs. PostgreSQL/PostGIS) pending David's
  decision. Rasters stay as GeoTIFF files; only per-cell values go into tables.
- **D-25** — Storage engine: **GeoPackage now** (SQLite with spatial support: real SQL, one file, no
  server, works in CI and QGIS). Schema designed to move to **PostgreSQL + PostGIS later** with one
  `ogr2ogr` load, if a dashboard, web app or concurrent writers appear. *Rejected for now:* PostGIS from
  the start (server, credentials and CI service break the one-command reproduction).

---

## Data gaps and opportunities (Colombia)

Gaps found while building the analysis. Each is a candidate for a later note, post or analysis; claims
marked *to verify* need a source before publication.

| # | Gap | Where found | Why it matters | Status |
|---|---|---|---|---|
| G-01 | Gridded soil data for Colombia (SoilGrids) are model predictions trained on few local soil profiles; uncertainty is likely high. | F1 step 4 | Soil losses (`f_loss`) are the most uncertain term; local soil sampling would cut uncertainty most. | *To verify:* count of WoSIS/SoilGrids training profiles in Colombia |
| G-02 | No open gridded exchangeable aluminium / base saturation. | Plan v0.4 (D-23) | Key driver of how much rock alkalinity is lost in acidic soils. | Open |
| G-03 | Official geological map: license of the GDB unclear (memoir CC BY 4.0 vs. SGC general terms). | F0b (D-08) | Blocks publishing derived rock-suitability maps. | Waiting for SGC |
| G-04 | Mining-title polygons (ANM) published without a license. | F0b (D-09) | Real quarries cannot be used openly; rock sources stay "potential". | Open |
| G-05 | Official boundaries (DANE MGN) not downloadable from the cloud environment; geoportal unavailable (HTTP 503) during checks. | F1 step 1 (D-11) | Forces non-official boundaries for clipping. | Open |
| G-06 | UPRA agricultural frontier service does not declare its version date. | F1 step 3 | Results cannot state which frontier version they use. | Open |
| G-07 | RUNAP condition "CONSTRUCCION" not documented in the data. | F1 step 2 (D-15) | Unclear whether those areas are legally protected yet. | Open |
| G-08 | No public, peer-reviewed ERW field data from Colombia found (only a conference abstract). | F0a research | Model parameters for the tropics cannot be calibrated locally. | From David's research; *to verify* in T0 |
| G-09 | MapBiomas Colombia (Collection 3.0) has no separate cropland class: crops and pasture share one mosaic class. | F1 step 5 (D-31) | Cannot tell cropland from cattle pasture with open national land-cover data. | Open; ESA WorldCover (D7) as possible cross-check |

## F2–F8 ⏳

Not started. See plan §8 for exit criteria.
