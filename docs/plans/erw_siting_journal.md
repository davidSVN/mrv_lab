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

## Resume point (2026-11-18)

Where the work stands, for the next session (F6 in this chat, David 2026-11-16).

| Done ✅ | In progress 🔄 | Next ⏳ |
|---|---|---|
| P0, F0a, F0b, F1 (steps 0–6b), F2, F3, F4 (38/39 ok, D-49, D-51–D-54), F5a, F5 | F6 (David's review pending), F7 (code written, D-60, not run) | F8, F9, F10, study guide |

**What exists.** One command rebuilds everything from `data/raw/`:
`uv run python analyses/01_erw_siting_colombia/analysis.py` (pilot boundaries, RUNAP, UPRA, SoilGrids,
MapBiomas, slope, CHIRPS + ERA5-Land climate, SGC lithology, potential rock sources, GeoPackage with
132,264 cells, filters, values and road routes, registry check). Code: `src/mrv_lab/erw_siting/`;
tests: `tests/erw_siting/` (90 passing). Parameters: `config/erw_siting/parameters/*.yaml` (38/39 ok, each recomputed from
its source and checked in every run).

**Where the data is.** `data/raw/` (downloads, SHA-256 pinned in `data/checksums.json`) and
`data/interim/erw_siting/` (clean layers, `erw_siting.gpkg`, QC maps in `qc/`). Both gitignored.

**Open items outside the code.**
- SGC written answer on publishing derived geology (D-08); email sent by David (reported 2026-11-18);
  until then F2/F3/F5 rock results are internal.
- Route-validation source (documented road distances) for ~20 example routes (D-47).
- Credentials: Copernicus CDS token saved in the cloud environment (never in the repo).

**How to work (rules R-01..R-11 below).** Explain before coding; implement only after David's OK;
verify every URL and licence before use; never invent values; update plan §0 and this journal in the
same commit as each decision.

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

## F0a — T0: does this map already exist? ✅ (closed 2026-11-18)

**Result (David's research R03a, cut 2026-11-13, not in the repo).** Verdict **PARTIAL**: no map
for Colombia meets the four criteria (Colombia, cell resolution, rock + transport, LCA / net
removal). Closest: a global web tool ("ERW Atlas", cost-based, no LCA, not peer reviewed); Cascade
Weathering Potential Explorer (soil/climate only, "not a site selection tool"); Strefler 2018,
Beerling 2020, Baek 2023 (global, no Colombian figure); Lefebvre 2019 (São Paulo) is the closest
method analogue. Colombian institutions publish no ERW or agrogeology map.

**Decision (David, 2026-11-18)**
- **D-55** — T0 closed; no further novelty search. Novelty is stated as "first for Colombia as far
  as searched (search documented)", built on the free angle: cell-level net removal with LCA,
  P(net > 0), national data (SGC, UPRA, roads), local rock chemistry and acid-soil losses.

**Checked against our sources.** Lefebvre 2019 break-even: the abstract says 990 ± 116 km, the body
994 ± 116 km (5 mm product); both appear in the paper. Unverified figures from R03a kept only as F7
cross-check candidates: Rinder & von Hagke 2021 grinding 18.9 kWh/t (< 100 µm) and 173 kWh/t
(< 10 µm) — the latter would be 2.6× our Bond value for the fine class; Ryan et al. 2024 (Costa
Rica): arc-volcanic mafic rocks give 3–5× lower CDR than oceanic-island basalts (relevant to Q-Vm
and J-Vi sources; K2-Vm is oceanic plateau).

### Earlier notes

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

## F1 — Data download and clipping (Meta, Tolima, Valle del Cauca) ✅

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
- **D-34** — *(rainfall part superseded by D-37)* Rainfall from **CHPclim v2** (Climate Hazards Center monthly climatology, 12 maps; period
  to verify in its documentation); the 30-year CHIRPS monthly series is kept for ENSO work (D-21).
  Temperature and evapotranspiration: **ERA5-Land** recommended (monthly means, CC BY, "January 1950 to
  present", updated monthly with a 2–3 month delay per its CDS page, checked 2026-11-13). David saw a
  "no longer updated" notice on a Copernicus page; the dataset page shows no such notice (likely the
  legacy CDS retired in 2024 — to confirm with the URL). A long-term average does not need recent
  months anyway. Needs a free CDS account + API key (secure credential form). Alternative without key:
  CHC CHTclim (temperature; variable to verify) and Hobbins RefET (marked "experimental" by CHC).
- **D-35** — Slope kept as a **continuous percentage**; the threshold (8 % or 12 %) is fixed in F5 with
  a cited source. The DEM is a surface model (trees, buildings); forests are removed by land cover.

- **D-37 (David, 2026-11-13)** — **All climate from ERA5-Land**, including rainfall (total
  precipitation). CHPclim has no published licence (checked the product page and the CHC data page:
  only a generic "All Rights Reserved" site footer); it was briefly started without the licence check
  (breach of R-04), stopped before any file was saved, and dropped. *Why:* fewer blockers, no third
  parties to contact, one consistent CC BY source. *Cost:* ~9 km reanalysis rainfall is less accurate in
  mountains than station-blended products. ERA5-Land token saved in the session environment (proxy
  injection, header `PRIVATE-TOKEN`); dataset licence (cc-by) accepted by David on 2026-11-13.

### Step 6b — Climate normals (CHIRPS + ERA5-Land, 1991-2020) ✅ (approved by David, 2026-11-14)

**Result (first run, 2026-11-13, pending review).** CDS job finished (~43 min queue); 4 variables ×
360 months on a 0.1° grid, pinned as GeoTIFFs. Plausibility check of the QC table: actual
evaporation and temperature look reasonable; **potential evaporation looks too high** (several
thousand mm/yr in the Llanos) and **rainfall looks too high on steep Andean/Pacific slopes**
(implausible maxima). Not used for any filter yet; options to be decided by David (gap G-10).

- **D-42 (David, 2026-11-14)** — Rainfall from **CHIRPS v2.0** monthly 1991-2020 (public domain,
  station-blended incl. IDEAM) instead of ERA5-Land rainfall; **drop ERA5-Land potential evaporation**
  and use **rainfall − actual evaporation** (ERA5-Land `e`) as the water term. Supersedes the rainfall
  part of D-37. ERA5-Land `tp` and `pev` stay downloaded, unused.

**Result with CHIRPS (2026-11-14, pending review).** 360 monthly windows pinned. Rainfall maxima now
physically plausible (Pacific slope of Valle highest, as expected); dry months up to ~4 in the inter-
Andean valleys. Temperature and actual evaporation unchanged. Numbers QC-only.

### Step 6a — Slope (Copernicus DEM GLO-30) ✅ (approved by David, 2026-11-13)

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
| G-10 | Open gridded climate for Colombia's mountains: ERA5-Land rainfall looks inflated on steep slopes and its potential evaporation looks implausibly high in the pilot; station-blended products have unclear licences (CHPclim). | F1 step 6b | Water-surplus term (rain − ET) is uncertain. | Open |
| G-11 | No open whole-rock analyses of the pilot's own rock sources (Western Cordillera basalts of Valle, Bolívar ultramafic complex, Valle gabbros); Kerr et al. 1997 paywalled. | F4 rock (D-49) | Rock chemistry comes from other Colombian localities; gabbro is a basalt proxy. | Open; David may supply Kerr 1997 PDF |

## F2 — Lithology (SGC geological map) ✅

**Purpose.** Locate rock suitable for ERW (mafic and ultramafic) on the SGC Mapa Geológico de
Colombia 2023. Internal use only: derived tables, maps and numbers are not published (git, posts)
until SGC answers in writing (D-08); code and rules are public.

**What.** `erw_siting/lithology.py`: download the File GDB (pinned), read the units layer `UC`
(3,218 polygons, 194 units, EPSG:4686 → 9377), list the rock types named in each description,
propose a class with written rules (main rock vs. minor mention vs. interbedded), let David review it
in `data/interim/erw_siting/geology/lithology_review.csv` (created once, never overwritten), and save
the classified units, a unit table, a QC map and a QC table (all gitignored).

**Decisions (David, 2026-11-13)**
- **D-38** — Keep **all three pilot departments** (Meta, Tolima, Valle del Cauca); D-05's "choose one
  Andean department" is withdrawn: the data are already processed, and comparing departments is
  valuable. Distances are computed **per cell, by road, in F5** (they drive transport emissions and,
  later, cost), not as a department summary. New future research question: how rock-source location
  per department changes emissions relative to removal.
- **D-39** — The table keeps **all 194 units**, with a `rock_types` column, so a future rock catalogue
  (F4 properties) can select units by rock type.
- **D-40** — Classes: **Apta** (mafic/ultramafic main rock), **Mixta** (interbedded or mixed, unknown
  proportion), **No apta**. Mixta does **not** count as rock supply by default; kept for a sensitivity
  scenario. Ultramafic units flagged (possible Ni/Cr).
- **D-41** — Rules in git; the unit table and review file (they contain SGC text) stay in
  `data/interim/` until SGC authorises publication.

**Result (approved by David, 2026-11-14).** Rule-based proposal produced for all units; results kept
internal (D-08). One unit has no description in the source (classified No apta).

- **D-43 (David, 2026-11-14)** — Manual review done: the proposed classes are accepted as they are
  (no `review_class` overrides); comments, if any, are handled later. Any citation of these results
  must cite the source map: Gómez, J., Montes, N.E. & Marín, E. (comps.) 2023, *Mapa Geológico de
  Colombia 2023*, escala 1:1.500.000, Servicio Geológico Colombiano (SOURCES.md D1), plus the
  classification rules in `src/mrv_lab/erw_siting/lithology.py`.

---

## F3 — Potential rock sources ✅ (approved by David, 2026-11-15)

**Purpose.** Points where a truck could load suitable rock: the origin of every road distance in F5.

**What.** `erw_siting/quarries.py`: national OSM roads (HOT export, ODbL), truck classes only; road
stretches within 5 km of Apta (then Mixta) rock are sampled every 500 m; each point gets its nearest
unit, exact access distance and road class; then at most one point per 5 × 5 km grid square is kept
(the one closest to the rock). Points and units are written to `rock_sources` and `rock_units` in
the GeoPackage (gitignored, SGC-derived).

**Decisions (David, 2026-11-14)**
- **D-46** — Truck road classes: motorway, trunk, primary, secondary, tertiary (+ links) and
  unclassified; no residential, service, track or path. Access distance up to **5 km** (David: 5 km
  rather than the proposed 1 km), recorded per point as `access_km`. Density one point per 5 km.
  Mixta points kept, flagged, excluded by default. 1 km / 5 km are modelling assumptions → F7.
- First implementation placed at least one point per OSM segment (OSM splits roads into many short
  segments) and produced 53,711 points; fixed to one point per 5 × 5 km square.

**Result (pending David's review).** Results internal (D-08). Some suitable rock (e.g. on the Pacific
slope) has no truck road within 5 km and gets no source; an island source has no road link to the
mainland and will be dropped by routing in F5. 59 tests pass.

## F5a — Data model (GeoPackage) ✅ (approved by David, 2026-11-14)

**Purpose.** One database where every 1 km cell carries every variable and every result, so the
analysis is SQL queries instead of loose files.

**Architecture.** Sources → `data/raw/` (pinned) → clean layers in `data/interim/` → **GeoPackage
`erw_siting.gpkg`** (SQLite with spatial support: real tables, keys, spatial indexes, no server) →
analysis, `results.json`, figures → later **PostgreSQL + PostGIS** with the same schema (F9).

**What.** `erw_siting/database.py` creates the empty GeoPackage: spatial tables `cells` (1 km
polygons) and `rock_sources` (points), and attribute tables `sources`, `cell_filters`, `cell_values`
(long: cell × variable × statistic), `rock_units`, `cell_routes`, `runs`, `cell_results`. Portable
SQL types, primary and foreign keys, SRID 9377, units in column names. Never overwrites an existing
file unless asked. Spatial tables are written through geopandas/OGR (GeoPackage triggers).

**Decisions (David, 2026-11-14)**
- **D-44** — GeoPackage now; new phase **F9: migration to PostGIS** when a dashboard / web app,
  several writers or national scale require it. 1 km cells; long table for soil and climate; border
  cells assigned to the department with most area; database gitignored, schema versioned.
- **D-45** — `cell_results` holds the explanation, not only the answer: candidate flag and excluding
  filter; CDR chain (max, dissolved fraction, soil losses, gross); emissions (grinding, transport,
  spreading); rock source and road km; break-even distance and margin; net removal per ha P5/P50/P95
  and probability of net > 0; lime demand (agronomic axis); ultramafic-source flag; data-quality
  flags. Out of scope on purpose: money costs, yield/nutrients, per-cell sensitivity, ENSO,
  municipality (F8). Totals per department are SQL queries, not stored.

**Result.** Empty database created with the 9 tables; 56 tests pass.

---

## F5 — Cell grid, filters, values and road routing ✅ (approved by David, 2026-11-16)

**What.** `grid.py` builds 132,264 cells of 1 km² (Meta 86,422; Tolima 24,603; Valle 21,239) and
fills `cell_filters` and `cell_values` (2.5 M rows). `routing.py` builds the truck-road graph
(6.4 M nodes) and runs one multi-source Dijkstra per scenario; `cells_pipeline.py` writes
`cell_routes` (2 scenarios) and the QC maps (distance with 20 example routes, influence areas).

**Decisions (David, 2026-11-15)**
- **D-47** — Route every cell; `scipy` (no new dependency); distance only; `road_km` = last mile
  (cell → road, straight) + network + source access (`access_km`); two scenarios (`apta`,
  `apta_mixta`); validate ~20 routes against a documented distance source (still missing). QC maps
  of distance and influence areas plus 20 drawn example routes.
- Schema change: `cell_routes` keyed by (cell_id, scenario), with `last_mile_km`.
- Fix after the first run: the truck-road subset splits into 4,352 components (the largest holds
  91 % of nodes; the rest connect only through excluded road classes). 10–20 % of cells were
  unreachable. Cells and sources now snap to the largest component only; the extra distance is
  recorded as last mile (mean 6.2 km, max 79 km). All cells reachable after the fix.

**Result (pending David's review).** Results internal (D-08: rock sources derive from SGC). First
reading: Meta depends on a very small suitable unit near its western edge, so its distances are
sensitive to that single unit; Tolima gets much closer rock only in the Apta+Mixta scenario.
Road/straight-line ratio (median) between 1.5 and 2.1. 64 tests pass. Influence areas: 84 % of Meta's
cells are supplied by one source (single-point dependency) → F7 sensitivity item; David declined an
immediate test.

---

## F4 — Parameter registry ✅ (closed 2026-11-16)

**What.** `config/erw_siting/parameters/*.yaml` (rock, capture, weathering, soil_losses, application,
lca) and `erw_siting/registry.py` (load, validate, list missing, read a value). 31 parameters, all
`status: missing` with no value until a verified source is found.

**Decisions (David, 2026-11-16)**
- **D-48** — Only `pyyaml` (no pydantic / pint); validation in plain code: `ok` needs value, unit
  and source (citation + DOI/URL); `missing` cannot carry a value; ranges must contain the value;
  known distribution types; unique ids. `registry.value()` refuses missing parameters (no silent
  defaults). Fill order: rock → emissions → weathering → soil → application, each group reviewed.

**Result.** Structure and tests in place (68 tests pass); values pending.

### Rock group ✅ (approved by David, 2026-11-16)

**What.** CaO, MgO, Na₂O, K₂O (wt%) for basalt, gabbro and ultramafic, computed from published
sample tables by `erw_siting/rock_chemistry.py` (downloads the PDFs, pins SHA-256, parses the tables
with `pdftotext`). `analysis.py` recomputes them and fails if `rock.yaml` drifts.

**Search.** Kerr et al. 1997 (J. Petrology, Western Cordillera basalts) not reachable: OUP and
Cardiff ORCA return 403; CiteSeerX / web.archive.org reset. Bolívar complex (Valle) data: Nivia 1996
abstract only. Redalyc and IRD copies blocked. Lewis et al. 2021 (6 non-Colombian basalts) used only
as a cross-check: lower CaO (5.7–9.4 %) and MgO (2.2–9.7 %) than the Colombian plateau basalts.

| Rock | Source | n | CaO | MgO | Na₂O | K₂O |
|---|---|---|---|---|---|---|
| Basalt | Kerr et al. 2002, Table 1 (MgO ≤ 12 wt%) | 11 | 10.48 [7.28–12.06] | 9.20 [7.09–11.20] | 2.14 [1.46–3.97] | 0.29 [0.08–1.12] |
| Gabbro | proxy = basalt set | 11 | same | same | same | same |
| Ultramafic | García-Casco et al. 2020, Table 1 | 49 (Na 38, K 36) | 0.71 [0.01–4.90] | 41.48 [30.00–45.27] | 0.04 [0.01–0.47] | 0.01 [0.00–0.07] |
| Picrite (F7 only) | Kerr et al. 2002 (MgO > 12 wt%) | 8 | 7.60 | 18.20 | 0.56 | 0.06 |

Median [min–max], wt% of rock as quarried.

**Decisions (David, 2026-11-16)**
- **D-49** — (1) Basis = rock as quarried: Kerr's dry-basis oxides × (1 − LOI/100); García-Casco
  already includes LOI. (2) Basalt = Kerr 2002 samples with MgO ≤ 12 wt% (the paper's high-MgO
  threshold); picrites excluded from the base value, used in F7. (3) Gabbro = basalt set as a proxy
  (no open Colombian gabbro analyses), flagged in notes. (4) Distribution triangular (min, median,
  max) per oxide; F7 should resample whole samples to keep CaO–MgO correlation. (5) Only aggregates
  are committed; PDFs and sample tables stay in `data/raw/` (redistribution unclear).

**Fix.** `registry.load` now keeps YAML nulls as `None` (pandas had turned them into NaN once
numbers and nulls mixed in a column, breaking validation); test added (73 tests pass).

**Limitations.** Basalts from SW Colombia picrite localities, not the Western Cordillera of Valle;
ultramafics from Antioquia (outside the pilot) and serpentinized (MgO overstates reactive Mg);
Na and K mobile in altered lavas.


### Parameters and scenarios in the database (approved by David, 2026-11-16)

**Why.** David wants to see the parameters in the database and, later, change them in a dashboard
to compare scenarios (rock types, settings). Missed in F5a: parameters were only planned as a JSON
column in `runs`, which cannot be filtered or joined (design oversight, acknowledged).

**Decisions (David, 2026-11-16)**
- **D-50** — "Base + overrides" model in the GeoPackage: `parameters` (read-only copy of the YAML
  registry, written every run; YAML stays the reviewed master), `scenarios` (rock type, route
  scenario, author, `citable`), `scenario_parameters` (only the values a scenario changes); `runs`
  now references `scenario_id`. Only the `base` scenario (all values sourced, nothing overridden)
  is citable; other scenarios are exploratory and never go to `results.json`. Scenario dashboard =
  new phase F10, after F7, on PostGIS (F9); routes precomputed per rock type so a rock change does
  not re-run Dijkstra live.

**Result.** 12-table schema; `database.write_parameters`, `add_scenario`, `scenario_values`;
75 tests pass.

### Emissions group (lca) and grain classes ✅ (approved by David, 2026-11-16)

**What.** 8 lca parameters + 3 grain-class definitions (new `grain.yaml`). `erw_siting/emission_factors.py`
downloads every source (SHA-256 pinned), checks each transcribed number against the source text
(21 regex checks) and recomputes the derived values; `analysis.py` fails on any mismatch.

| Parameter | Value | Range | Source |
|---|---|---|---|
| grid_ef_kgco2_per_kwh | 0.220 | 0.112–0.220 | UPME Res. 085/2026 (2024); 1198/2024 (2023: 0.177); 705/2024 (2022: 0.112) |
| diesel_ef_kgco2_per_l | 2.689 | — | FECOC 2016, Tabla 5: 10.180 kg CO2/gal |
| truck_l_diesel_per_t_km | 0.0204 | 0.0159–0.0364 | UPME/IDB freight baseline, Tabla 2.8, median of 7 loaded-only heavy diesel fleets |
| empty_return_factor | 1.42 | 1.0–1.42 | SICE-TAC C3S3 March 2024 (via ANDI): empty 15.55 vs loaded 6.48 km/gal |
| grinding_kwh_per_t_coarse / medium / fine | 9.02 / 22.97 / 67.11 | Wi 17.10 low end | Crushing 5.45 kWh/t (Lefebvre 2019) + Bond from 5 mm, Wi 20.41 (Ruan 2026) |
| spreading_l_diesel_per_t | 2.02 | — | Lefebvre 2019, Table 1: 1.73 kg diesel/t ÷ 0.856 kg/L (FECOC) |
| p80_um_coarse / medium / fine | 1000 / 100 / 10 µm | — | Definition (sizes modelled by Ruan 2026) |

Cross-check: transport 0.0204 × 2.689 × 1.42 = 0.078 kg CO2/t-km vs 0.062 in Renforth 2012 (via Ruan 2026).

**Decisions (David, 2026-11-16)**
- **D-51** — (1) Grain classes P80 = 1000 / 100 / 10 µm (coarse / medium / fine), stored as
  definition parameters in `grain.yaml`; grinding and `f_diss` must use them. (2) Spreading diesel
  per tonne of rock (`spreading_l_diesel_per_t`, L/t) instead of per hectare: fuel grows with the
  mass spread. (3) Truck fuel from loaded trips only + explicit empty return factor 1.42 (a rock
  truck returns empty to the quarry); range low end 1.0 = backhaul. Values: conservative choices
  (Wi 20.41 not 17.10; diesel 100 % fossil; latest, highest grid factor of 2022–2024).

**Search notes.** Strefler et al. 2018 (ERL, CC BY) grinding curve is in an SI blocked by the
publisher (403); main text (0.07 GJ/t at 50 µm ≈ 19 kWh/t) agrees with Bond. Japan ERW study
(0.31 L/t spreading) and the Northern California LCA (Wi 18.56) paywalled or unavailable: not used.
Minambiente 2026 emission-factor document covers black carbon / criteria pollutants, not CO2.

**Limitations.** Bond's law underestimates below ~70 µm (fine class is a lower bound); grid factor
depends on hydrology (El Niño); empty-return ratio from the tractor-trailer model, not the dump
truck; spreading from one Brazilian study without range.

**Refactor.** `io.pdf_text` and `registry.check_values` shared by the rock and lca groups.

### Weathering group ✅ (approved by David, 2026-11-16)

**What.** The 5 placeholders (`f_diss_coarse/medium/fine`, one activation energy, reference
temperature) could not hold a fixed `f_diss`: it depends on cell temperature, rock type and horizon.
Replaced by 9 kinetic parameters; `erw_siting/weathering.py` computes `f_diss` per cell:
`min(1, SSA(P80) × WR × M × 3.155e7 s/yr × years × exp(−Eₐ/R (1/T − 1/T_ref)))` (Strefler et al. 2018,
Eq. 2). Quoted numbers checked against the sources (10 regex checks); shared helpers in
`erw_siting/literature.py`.

| Parameter | Value | Range | Source |
|---|---|---|---|
| ssa_coef_m2_per_g / ssa_exponent | 69.18 / −1.24 | — | Strefler 2018 (SSA fit, SI B) |
| log10_wr_basalt_mol_m2_s | −10.53 | −12.63 to −9.55 | Strefler 2018, pH 7, 25 °C |
| log10_wr_ultramafic_mol_m2_s | −9.86 | −9.95 to −9.77 | Strefler 2018 (dunite) |
| molar_mass_basalt / _ultramafic (g/mol) | 125 / 140.7 | — | Strefler 2018 |
| activation_energy_kj_per_mol_basalt | 45.2 | 40.6–78.0 | Palandri & Kharaka 2004: labradorite neutral (range diopside–augite) |
| activation_energy_kj_per_mol_ultramafic | 79.0 | — | Palandri & Kharaka 2004: forsterite neutral |
| reference_temperature_c | 25 | — | Definition (temperature of both sources' rates) |

Basalt at 25 °C after 10 years: coarse 0.015, medium 0.27, fine 1.0 (30 years: 0.046 / 0.80 / 1.0).
At 20 °C the rate is 73 % of the 25 °C rate; at 15 °C, 53 %.

**Decisions (David, 2026-11-16)**
- **D-52** — (1) `f_diss` is computed per cell from kinetic parameters, not stored as fixed values.
  (2) No water factor (no sourced function; Strefler restricts to humid regions); dry months from
  CHIRPS are a flag only; plan §5.2 updated. (3) Basalt activation energy = labradorite, neutral
  mechanism (plagioclase dominates; WR is at pH 7). Gabbro uses basalt kinetics (proxy).

**Fix.** `io.download_file` now sends a generic User-Agent (USGS refuses Python's default) and
refuses a `.pdf` download that is not a PDF (IOP served a bot-check page that had been pinned;
removed before commit). Test added.

**Limitations.** WR spans three orders of magnitude and is lab-based (abiotic field rates may be
~100× lower); constant-surface model overestimates long horizons; no pH term (acid soils would
dissolve faster); ultramafic rate is for fresh dunite (pilot ultramafics are serpentinized); gabbro
is crystalline and likely slower than the basalt proxy. Horizon (10 vs 30 years) decided in the
application group; recommendation: 10 base, 30 in F7.

### Capture and application groups ✅ (decided on the sources, David delegated, 2026-11-16)

**What.** `erw_siting/capture.py`: R_CO2 counted by charges, sources downloaded, pinned and
checked (7 regex checks). David asked Claude to choose from credible sources and give the argument.

| Parameter | Value | Range | Source |
|---|---|---|---|
| eta_mol_co2_per_mol_charge (renamed from `_per_mol_cation`) | 0.831 | 0.70–0.85 | Renforth & Henderson 2017, Eq. 11 (400 µatm, S 35, 17 °C); range from "1.4 to 1.7" CO₂ per divalent cation |
| application_rate_t_per_ha | 20 | 5–50 | Lefebvre 2019 (5 current practice, 20 field trials, 50 literature maximum) |
| horizon_years | 10 | 10–30 | Definition; 30 = Lewis 2021 RTM horizon |

R_CO2 with the registry rock chemistry: basalt (and gabbro proxy) 0.331, ultramafic 0.763 t CO₂/t
(theoretical maximum, before f_diss and f_loss). Cross-check: Ruan 2026 reports 0.30 ± 0.08 for
basalts worldwide.

**Decisions (2026-11-16)**
- **D-53** — (1) η = 0.831 from the primary source, not the 0.86 that Lewis 2021 quotes for the
  same conditions; parameter renamed "per mole of charge". (2) Capture counted by charges (Lewis
  Eq. 4): every oxide releases 2 moles of charge per mole; Lewis Eq. 5 (0.5ω for Na₂O/K₂O) and its
  Table 6 R_CO2 values are not reproducible (up to 15 % off with ω = 1.72) and are not used.
  (3) Application rate 20 t/ha base (5–50). (4) Horizon 10 years base, 30 in F7.

**Limitations.** Ocean pathway assumed (soil carbonate precipitation roughly halves capture, not
modelled); η at 17 °C ocean conditions; dose from Brazil / literature (no Colombian ERW dose found);
horizon is a modelling choice.

### Soil-loss group ✅ (decided on the sources, David delegated, 2026-11-16) — F4 closed

**What.** `erw_siting/soil_losses.py`: f_loss by topsoil pH class; sources pinned, 7 quotes checked.

| Parameter | Value | Range | Source |
|---|---|---|---|
| f_loss_acid_soil | 0.68 | 0.35–0.68 | Su et al. 2026: 1 − 1/3.1 (largest overestimate, acidic soil); low end 1 − 1.30/2 |
| f_loss_neutral_soil | 0.33 | 0–0.33 | Su et al. 2026: 1 − 1/1.5 (smallest overestimate); low end 0 = freshwater ACE ≈ 1 (Bertagni & Porporato 2022) |
| acid_soil_ph_threshold | 5.5 | 4.5–6.5 | Middle of the ACE transition (Bertagni & Porporato 2022) |
| exchangeable_al_cmolc_per_kg | missing | — | Not in SoilGrids (G-02); not used by the two-class rule |

Pilot cells with SoilGrids pH < 5.5: Meta 99 % (median pH 5.05), Tolima 81 % (5.38), Valle 74 % (5.28).

**Decisions (2026-11-16)**
- **D-54** — Two pH classes instead of a pH–CEC function: the only quantified field-like evidence
  (Su et al. 2026) reports a range by soil acidity, and the theory (Bertagni & Porporato 2022) gives
  a sharp transition, not a smooth curve. Conservative base values (measured overestimates), theory
  as the low end of the ranges. Exchangeable Al stays missing and unused; an acidity mass balance
  (alkalinity consumed before capture starts) is future work.

**Search notes.** Su et al. 2026 full text (ACS) paywalled: only the PubMed abstract is used; the
mapping of 0.63–1.30 mol CO₂ per divalent cation to individual pH values is not in the abstract.
arXiv 2607.01835 ("Subsoil acidity causes long delays…") and a Frontiers in Climate 2025 paper on
strong acids were found but not used (not read in full).

**Limitations.** One experiment, wollastonite not basalt, abstract only; SoilGrids pH is modelled
(G-01); two classes create a step at pH 5.5; time dynamics (acidity consumed first, capture later)
ignored. With this rule the acidic Meta keeps only 32 % of the theoretical capture.

**F4 result.** 39 parameters, 38 `ok`, each value recomputed by code and checked against its
source text in every run; 1 `missing` (exchangeable Al, unused).

---

## Study guide for David (requested 2026-11-16) ⏳

**What.** At the end, a study guide in Spanish (private page, not in the repo) explaining every
chemical and technical term and every formula used, with the analysis's own numbers as worked
examples and where each lives in the code. Terms are collected here as they appear.

**Term backlog**
- Rocks and minerals: mafic / ultramafic / felsic; basalt, gabbro, picrite, dolerite; dunite,
  peridotite, harzburgite, lherzolite; serpentinite and serpentinization; olivine (forsterite),
  pyroxene (augite, diopside), plagioclase (labradorite), basaltic glass; oceanic plateau (CCOP);
  SGC unit codes (K2-Vm, K2-Pm, K2-Pu…); Apta / Mixta / No apta.
- Chemistry: oxides and wt%; LOI, dry basis vs rock as quarried; mole and molar mass; cations
  (monovalent Na⁺ K⁺, divalent Ca²⁺ Mg²⁺) and charge; alkalinity; bicarbonate vs carbonate;
  η (CO₂ per mole of charge), ω = 2η, R_CO2 (theoretical capture per tonne); Lewis Eq. 5 vs Eq. 4
  (the 0.5ω issue); ocean vs soil carbonate pathway; pCO2, salinity; atomic weights (IUPAC);
  primary vs secondary source (Lewis quoting 0.86 vs Renforth & Henderson 0.831).
- Weathering: dissolution; specific surface area (SSA); weathering rate WR and log10 units;
  Arrhenius law, activation energy, reference temperature; dissolved fraction f_diss; constant
  surface vs shrinking core; pH and acid soils.
- Soil: pH, CEC, exchangeable Al, base saturation, f_loss, lime demand; Ni / Cr and asbestos risks;
  alkalinity carbon-capture efficiency (ACE) and the pH 4.5–6.5 transition; strong acid anions;
  soil organic carbon mineralization; inorganic carbon; wollastonite (CaSiO₃).
- Grinding and logistics: P80 / F80, Bond's law and work index; t·km, SFC / SFC*, empty return;
  diesel factor (FECOC); grid factor (inventory vs CDM, combined margin OM / BM).
- Accounting and statistics: CDR, ERW, MRV, LCA, net removal, break-even distance and margin;
  candidate cell and hard filters; scenario vs run; median, range, triangular distribution,
  Monte Carlo, P(net > 0), sensitivity.

---

## F6 — Deterministic net removal 🔄 (code and first run 2026-11-18; David's review pending)

**What.** `erw_siting/net_removal.py` builds one row per cell (filters, mean temperature, topsoil pH,
dry months, Apta route, source rock class) and computes for the candidate cells:
`cdr_gross = R_CO2 × f_diss × (1 − f_loss)`; `net = cdr_gross − e_grind − e_transport − e_spread`
(t CO₂/t rock); `net_ha = net × 20 t/ha ÷ 10 yr`; break-even distance and margin. One run per grain
class (`base` = medium, `grain_coarse`, `grain_fine`), stored in `runs` + `cell_results` with the
effective parameter values, filters and code commit. Internal QC: `qc/f6_summary.csv`,
`qc/f6_net_ha.png`, `qc/f6_margin_km.png`. Runs in ~30 s.

**Decisions (David, 2026-11-18)**
- **D-56** — (1) Candidate cell = protected < 50 %, frontier "No condicionada" ≥ 50 %, agricultural
  use ≥ 50 %, slope > 12 % on < 50 % of the cell; every failed rule is listed in `excluded_by`.
  Conditioned frontier and the 8 % slope go to F7. (2) Base grain = medium (100 µm); coarse and fine
  computed as scenarios. (3) Rock class per source: ultramafic flag → ultramafic; gabbro / norite
  named first → gabbro (basalt proxy); otherwise basalt; Q-Vm and J-Vi flagged `arc_volcanic_source`.
  (4) Route scenario: Apta sources only (Apta + Mixta in F7).

**Schema.** `scenarios.grain_class`; `cell_results.rock_class`, `net_tco2_per_t`,
`net_ha_tco2_per_ha_yr` (deterministic; the P5/P50/P95 columns wait for F7). Inserts now name their
columns.

**Result (internal, D-08).** Candidate cells: Meta 14,936; Tolima 3,943; Valle 3,098 (these counts
use no SGC data). Checkpoint passed: net removal is positive in part of every department.
Net-removal numbers depend on SGC-derived rock sources and stay out of the repo until the SGC
answers; they are in `data/interim/erw_siting/qc/f6_summary.csv`.

**Serpentinization correction (David, 2026-11-18)**
- **D-57** — The ultramafic rate is no longer fresh dunite: `log10 WR = −9.86 + log10((1 − s) +
  s · 10^r)`, with s = serpentinized share = median of LOI / 12.5 wt% over García-Casco's 49 samples
  (0.70; IQR 0.56–0.79; "a fully serpentinized peridotite yields ca. 12–13 wt % H2O") and r =
  lizardite − forsterite neutral log k (Palandri & Kharaka 2004: −12.40 − (−10.64) = −1.76; range to
  chrysotile −1.36). Result −10.37 instead of −9.86: about 3× slower. Two new weathering parameters
  (`serpentinized_fraction_ultramafic`, `log10_rate_ratio_serpentine_forsterite`); 40/41 ok.
  Limits: surface shares taken equal to volume shares; Ea stays forsterite; samples from Medellín.
  Asbestos (chrysotile) risk of grinding serpentinite is a flag for F8, not modelled.

**Configurable filters and map code (David, 2026-11-18)**
- **D-58** — Principle: every variable brought into the analysis must be usable as a filter or
  parameter in future scenarios and in the F10 dashboard (soil properties, rock type and source,
  temperature, rainfall, evaporation, dry months, slope, elevation, department, cell area, quarry,
  grain, horizon, and the Monte Carlo P5 / P50 / P95). First step: candidate filters are now
  settings (`net_removal.DEFAULT_FILTERS`: protected and frontier thresholds, frontier types,
  land-use share, **include natural grassland / savanna** (new `cell_filters.grassland_frac`,
  MapBiomas class 12), slope class 8 / 12 %); stored per scenario in `scenarios.filters_json` and
  per run in `runs.parameters_json`. A scenario with changed filters is not citable.
  Gap for F10: elevation is not stored per cell yet (only slope).
- Why grey dominates the Meta maps: only 17 % of Meta cells are candidates (frontier excludes 65 %,
  land use 63 %; 18 % fail only on land use, likely Llanos savanna with extensive grazing, which
  MapBiomas maps as natural grassland). Candidate cells with margin near 0 were also drawn almost
  white, close to the light grey.
- Map code (written, not run; next full run produces them): darker grey for non-candidates;
  department outlines and names; `f6_exclusion_reasons.png` (one panel per filter);
  `f6_potential_*.png` (emissions, margin, net per ha for every cell as if farmed, candidates
  outlined). `grassland_frac` needs the F5 rebuild (next full run).
- Monte Carlo storage for F7: keep per-cell draws (or histograms) outside the GeoPackage
  (Parquet, ~66 M values) so the F10 dashboard can show each cell's curve and a 3D column view.

**Savanna decision (David, 2026-11-18)**
- **D-59** — Natural grassland / savanna stays **out** of the base candidate land
  (`include_grassland = False`, as D-31/D-56): the analysis keeps the current agricultural classes.
  Future work (plan "Future"): analyse cropland vs pasture zones separately, to compare ERW on land
  for food production versus grazing or other rural uses. No further change to the grassland code.

**Readings to check in F7 (qualitative).** Coarse grain is net negative almost everywhere; the
eastern Meta is beyond break-even distance; ultramafic sources dominate the Tolima result and
use the fresh-dunite rate (pilot ultramafics are serpentinized) — the most fragile part of F6.

---

## F7 — Monte Carlo and sensitivity 🔄 (code written 2026-11-18; not run yet)

**What.** `erw_siting/monte_carlo.py`: for each F6 grain run, 1,000 draws (seed 20261118) of every
parameter with a source range (triangular min / base / max; the same draw for every cell) and a
whole-sample bootstrap of rock chemistry; the F6 chain (`net_removal.chain`, shared with F6) is
evaluated per draw. Per-cell draws of net removal (float32) go to
`data/interim/erw_siting/monte_carlo/<run_id>.npz` with the parameter and rock draws; P5 / P50 /
P95 per ha and year and P(net > 0) go to `cell_results`; `runs.seed` is set. Tornado (one parameter
at a time to its range ends, department medians) to `qc/f7_tornado.csv` / `.png`.
`erw_siting/sensitivity.py`: five deterministic medium-grain scenarios stored as `scenarios` + runs
(horizon 30 yr; conditioned frontier; slope 8 %; Apta + Mixta; Meta without its main rock unit,
re-routed) and summarised in `qc/f7_assumptions.csv`. F6 refactor: `net_removal.chain` (plain
arrays) and `run_scenario` (adds a scenario without clearing others).

**Decisions (David, 2026-11-18)**
- **D-60** — (1) 1,000 draws, fixed recorded seed. (2) Triangular (min, base, max) for parameters
  with a range; fixed: definitions (P80, reference temperature, pH threshold) and choices tested
  as scenarios (application rate, horizon); rock chemistry resampled by whole sample (a blank
  oxide takes the set median). (3) Assumption scenarios 1–5 now; recent climate and Rinder &
  von Hagke fine grinding in a second round. (4) Per-cell draws stored as NumPy `.npz` (no new
  dependency); Parquet can come with F9 / F10.

---

## F2–F8 ⏳

Not started. See plan §8 for exit criteria.
