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

### Step 2 — Protected areas (RUNAP) 🔄

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

**Result (pending David's review).** Mask, QC map and QC table written to `data/interim/erw_siting/`
(gitignored). First reading of the QC table: national natural parks dominate the excluded area in
Meta and Tolima; in Valle del Cauca sustainable-use categories weigh more, so D-14 matters most
there. Numbers stay QC-only until they come from `results.json`. 17 tests pass.

### Steps 3–6 ⏳

UPRA agricultural frontier (D4), SoilGrids (D8, needs `rasterio`), MapBiomas (D6), slope / rainfall /
temperature (D11, D9, D10). Each will get its own entry here.

---

## F2–F8 ⏳

Not started. See plan §8 for exit criteria.
