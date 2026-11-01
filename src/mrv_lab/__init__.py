"""mrv_lab: shared logic for public, reproducible carbon MRV analyses.

Modules:
    io           Paths relative to the repo root (loaders/downloaders come later).
    plotting     Single figure style, colorblind-safe palette, PNG + SVG export.
    uncertainty  Uncertainty discounts, confidence intervals, Monte Carlo (stub).
    sampling     Statistical power and sample size for soil sampling (stub).
    lca          Net removal accounting (stub).
"""

from importlib.metadata import version

__version__ = version("mrv-lab")
