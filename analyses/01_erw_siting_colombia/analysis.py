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
    print(f"Skeleton OK. Raw data dir: {raw_dir.relative_to(io.repo_root())}")
