"""Paths relative to the repository root.

No absolute paths are hardcoded anywhere in the repo (CLAUDE.md §9): every
location is derived from :func:`repo_root`. Data loaders and downloaders will
live here too, added with the analyses that need them.
"""

from pathlib import Path


def repo_root() -> Path:
    """Return the repository root (the directory holding ``pyproject.toml`` and ``src/mrv_lab``).

    Raises:
        FileNotFoundError: if the package is not running from a checkout of the repo.
    """
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").is_file() and (parent / "src" / "mrv_lab").is_dir():
            return parent
    raise FileNotFoundError("Could not locate the mrv-lab repository root.")


def data_dir() -> Path:
    """Return ``data/``."""
    return repo_root() / "data"


def raw_dir() -> Path:
    """Return ``data/raw/`` (gitignored by default)."""
    return data_dir() / "raw"


def processed_dir() -> Path:
    """Return ``data/processed/`` (committed only if the source license allows it)."""
    return data_dir() / "processed"


def analyses_dir() -> Path:
    """Return ``analyses/``."""
    return repo_root() / "analyses"


def analysis_dir(slug: str) -> Path:
    """Return ``analyses/<slug>/``, e.g. ``analysis_dir("01_cdr_buyers")``."""
    return analyses_dir() / slug


def figures_dir(slug: str) -> Path:
    """Return ``analyses/<slug>/figures/``."""
    return analysis_dir(slug) / "figures"
