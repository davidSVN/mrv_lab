# mrv-lab

Public, reproducible analyses of carbon MRV data (Measurement, Reporting, Verification):
carbon dioxide removal (CDR) markets, certificate uncertainty, soil sampling, life-cycle
assessment (LCA) and the EU Carbon Border Adjustment Mechanism (CBAM).

Every number published from this work is computed by code in this repo and stored in the
`results.json` of the analysis that produced it.

## Analyses

| # | Analysis | Question | Key result | Data |
|---|---|---|---|---|
| 01 | [Where does ERW make sense in Colombia?](analyses/01_erw_siting_colombia/) | _In progress_ | — | — |

Each analysis lives in `analyses/NN_slug/` with a README (Question · Data · Method ·
Result · Limitations · Reproduce), an `analysis.py`, a `results.json` and its figures.
Start new ones from [`analyses/00_template/`](analyses/00_template/).

## Reproduce

Requirements: [uv](https://docs.astral.sh/uv/). uv installs Python 3.12 if needed.

```bash
git clone https://github.com/davidSVN/mrv_lab.git
cd mrv_lab
uv sync
uv run python analyses/NN_slug/analysis.py
```

Raw data is not always committed. When a source does not allow redistribution, the
analysis includes a `download.py` that fetches it into `data/raw/`; see the analysis
README and [`data/SOURCES.md`](data/SOURCES.md).

Quality checks (same as CI):

```bash
uv run ruff check . && uv run ruff format --check . && uv run pytest
```

## Repository layout

```
data/SOURCES.md      registry of every data source, its license and redistribution status
data/raw/            raw downloads (gitignored by default)
data/processed/      derived data, committed only when the source license allows it
src/mrv_lab/         shared library: io, plotting, uncertainty, sampling, lca
analyses/NN_slug/    one folder per analysis
tests/               tests for src/mrv_lab
```

## Licenses

- **Code:** MIT, see [LICENSE](LICENSE).
- **Data:** keeps the license of its original source. The MIT license does not apply to
  third-party data. Check [`data/SOURCES.md`](data/SOURCES.md) and each analysis README
  before reusing any data or derived figures.
