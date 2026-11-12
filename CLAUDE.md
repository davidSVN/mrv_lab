# CLAUDE.md — mrv-lab

Instructions for Claude Code in this repository. Read fully at the start of every session.

## 1. What this repo is
Public, reproducible analyses of carbon MRV data (Measurement, Reporting, Verification):
carbon dioxide removal (CDR) markets, certificate uncertainty, soil sampling, LCA, CBAM.

- Owner: David (data analyst, mechatronic engineer).
- Hard rule: **every number David publishes (LinkedIn, talks, CV) must be computed by code in this repo.**
- Audience: MRV practitioners, CDR buyers/developers, verifiers, recruiters. Global, English.

## 2. Private context
If `PRIVATE_CONTEXT.md` exists at the repo root, read it at session start.
- It is gitignored. **Never** copy its contents into tracked files, commits, issues, PRs or figures.
- Before any `git add`, confirm `PRIVATE_CONTEXT.md` is listed in `.gitignore`.

## 3. How to work with David
- Talk to David in Colombian Spanish (tú). Code, comments, READMEs and commits in English.
- Go step by step: propose a short plan, wait for his OK before large changes (new analysis, new dependency, restructure).
- Concise. No filler, no praise.
- When you change or improve something: one line for WHAT, one line for WHY.
- **Never invent** data, sources, URLs, licenses or numbers. If something can't be computed from data in the repo, say so.
- If a data source's license or terms of use are unclear: stop and ask. Don't download or commit until resolved.
- If David's idea has a technical flaw, say it directly with the reason.

## 4. Stack
- Python 3.12, `uv` for environment and dependencies (`uv sync`, `uv run ...`, `uv add ...`).
- Core: pandas, numpy, scipy, matplotlib. Optional: polars, plotly, statsmodels (ask before adding).
- Notebooks: **jupytext percent-format `.py` files are the source of truth** (`# %%` cells). `.ipynb` is optional and generated. Why: clean diffs and reviewable code.
- Quality: ruff (lint + format), pytest. CI on GitHub Actions runs the same.

## 5. Structure
```
mrv-lab/
├── CLAUDE.md
├── README.md                  # what it is, analysis index, how to reproduce
├── LICENSE                    # MIT for code. Data keeps its source license
├── pyproject.toml
├── .gitignore                 # includes data/raw/, .env, PRIVATE_CONTEXT.md
├── config/                    # scenario + parameter registry YAMLs, one subfolder per analysis
├── data/
│   ├── SOURCES.md             # registry of every data source (see §7)
│   ├── raw/                   # gitignored by default
│   ├── interim/               # intermediate pipeline outputs (gitignored)
│   └── processed/             # committed only if the license allows it
├── src/mrv_lab/
│   ├── __init__.py
│   ├── io.py                  # loaders / downloaders
│   ├── plotting.py            # single style + palette + export helpers
│   ├── uncertainty.py         # discounts, confidence intervals, Monte Carlo
│   ├── sampling.py            # statistical power, sample size
│   ├── lca.py                 # net removal accounting
│   └── erw_siting/            # ERW-specific logic for analysis 01
├── analyses/
│   └── NN_slug/
│       ├── README.md
│       ├── analysis.py        # jupytext percent format
│       ├── download.py        # only if raw data can't be committed
│       ├── results.json
│       └── figures/
├── docs/
│   ├── plans/                 # analysis specs (e.g. erw_siting_colombia.md)
│   └── adr/                   # architecture decision records
├── tests/
└── .github/workflows/ci.yml
```

## 6. Analysis contract (every `analyses/NN_slug/`)
1. `README.md` with exactly these sections:
   - **Question** — one sentence.
   - **Data** — source, URL, access date, license, what is redistributed here.
   - **Method** — steps, assumptions, formulas.
   - **Result** — key numbers (taken from `results.json`) + main figure.
   - **Limitations** — what this does NOT show; biases of the source.
   - **Reproduce** — one command.
2. `analysis.py` runs end-to-end from raw data: `uv run python analyses/NN_slug/analysis.py`.
3. `results.json`: every number that may be quoted publicly. Schema per entry:
   `{"key": "...", "value": 0.0, "unit": "...", "description": "...", "as_of": "YYYY-MM-DD"}`.
   Posts quote these keys, never ad-hoc numbers.
4. Reusable logic goes to `src/mrv_lab/` with tests. Analysis scripts stay thin.
5. Each analysis must add **one own reading** on top of the raw data (a cut, a ratio, a comparison, a new chart). Reproducing what the source shows is OK; just make the added reading explicit in the README.

## 7. Data rules
- `data/SOURCES.md` table columns: source · URL · access date · license / terms · redistribution allowed (yes / no / unclear) · quality (primary / specialized press / blog) · notes.
- Raw data: gitignored unless the license explicitly allows redistribution. If not allowed: commit `download.py` instead (credentials from `.env`).
- Derived/processed data: commit only if the license allows it. If unclear, commit aggregates only and ask David.
- Prefer primary sources (registries, regulators, filings) over press or blogs.
- Never commit: credentials, `.env`, confidential or personal data, client or interview data.
- Don't name private companies or people in figures/READMEs unless they are part of the public data source itself.

## 8. Figure style (all figures through `src/mrv_lab/plotting.py`)
- Title = the finding, not the topic ("4 buyers hold X% of contracted tonnes", not "Buyer concentration").
- Subtitle = what is measured, unit, period.
- Footer = `Source: <source> (accessed YYYY-MM-DD) · Analysis: github.com/<user>/mrv-lab`.
- Colorblind-safe palette, defined once. Highlight one series; grey the rest. No 3D, no pies.
- Export: PNG 1080×1350 (LinkedIn 4:5) + SVG, to `figures/`.
- Units always explicit (tCO2e, USD/t, %).

## 9. Code conventions
- Type hints. Docstrings state units. Unit in variable names when ambiguous (`tonnes_tco2e`, `price_usd_per_t`).
- No hardcoded absolute paths: use `pathlib` relative to repo root.
- Deterministic: fix random seeds; record them in `results.json`.
- Tests: required for `src/mrv_lab/`. Not required for analysis scripts (CI only checks they run, if data is available).

## 10. Quality gate before every commit
```
uv run ruff check . && uv run ruff format --check . && uv run pytest
```
Plus: the touched analysis runs from a clean state.

## 11. Git
- One branch per analysis: `analysis/NN-slug`. Small branches for infra: `chore/...`.
  Exception: a branch auto-named by a Claude Code cloud session (`claude/...`) may be used as-is.
- Archived work lives in `archive/...` branches (e.g. `archive/erw-3d-viewer-v0`: virtual ERW field
  + 3D viewer prototype, superseded). Do not branch new work from them.
- Conventional commits (`feat:`, `fix:`, `docs:`, `chore:`, `data:`).
- Never push to `main` or open a PR without David's OK. Never force-push.

## 12. Roadmap (public index; order can change)
| # | Analysis | Data |
|---|---|---|
| 01 | Where does ERW make sense in Colombia? Site screening by region. Spec: `docs/plans/erw_siting_colombia.md` | SGC, ANM, UPRA, MapBiomas, SoilGrids, CHIRPS, ERA5-Land, Copernicus DEM, OSM, UPME (D1–D18 in spec) |

No deadlines. Priorities and dates are set only by David, per conversation.

At session start, read the plan's status (§0 of `docs/plans/erw_siting_colombia.md`) and
`docs/plans/erw_siting_journal.md` (steps, decisions D-xx, working rules R-xx, results). Every decision
updates both in the same commit.

## 13. Session close (only on request)
Only when David writes `cierre de sesión`, give him this block, in Spanish. Never otherwise:
```
CIERRE DE SESIÓN — chat 03 Repo — [fecha]
Hecho:
- ...
Decisiones:
- ...
Hallazgos que afectan a otros chats:
- [chat X]: ...
Bloqueos:
- ...
Próxima acción:
- ...
KPI:
- análisis publicados N · tests verdes sí/no
```

## 14. First session: bootstrap
If the repo is empty (only README/LICENSE), propose and, after OK, create:
1. `.gitignore` (Python + `data/raw/`, `.env`, `PRIVATE_CONTEXT.md`) — **first, before anything else**.
2. `pyproject.toml` (uv, Python 3.12, deps from §4, ruff + pytest config).
3. `src/mrv_lab/` with `__init__.py` and `plotting.py` (style + export).
4. `data/SOURCES.md` (empty table), `analyses/` with a template folder `00_template/`.
5. `tests/test_smoke.py`, `.github/workflows/ci.yml` (uv sync, ruff, pytest).
6. README with project description + empty analysis index.
Then: review CDR.fyi terms of use before writing analysis 01.
