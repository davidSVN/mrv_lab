"""Light history of results (decision D-62, option A).

Every F6 / F7 run copies its small summary tables to
``data/interim/erw_siting/qc/history/<YYYY-MM-DD>_<commit>/`` so versions can be compared after a
parameter changes. The database and the Monte Carlo draws are not copied: they are reproduced from
the code version (git commit) and the recorded seed.
"""

import shutil
import subprocess
from datetime import date
from pathlib import Path

from mrv_lab import io


def version_tag() -> str:
    """``<YYYY-MM-DD>_<short commit>`` (``nocommit`` outside git); ``-dirty`` if uncommitted."""
    root = io.repo_root()
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=root, capture_output=True, text=True
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=root,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except OSError:
        commit, dirty = "", ""
    return f"{date.today().isoformat()}_{commit or 'nocommit'}{'-dirty' if dirty else ''}"


def history_dir() -> Path:
    """``data/interim/erw_siting/qc/history/`` (gitignored)."""
    return io.interim_dir() / "erw_siting" / "qc" / "history"


def snapshot(files: list[Path], tag: str | None = None) -> Path:
    """Copy ``files`` into the history folder of this version; returns the folder."""
    folder = history_dir() / (tag or version_tag())
    folder.mkdir(parents=True, exist_ok=True)
    for f in files:
        shutil.copy2(f, folder / f.name)
    return folder
