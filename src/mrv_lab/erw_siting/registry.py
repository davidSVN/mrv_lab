"""Parameter registry for the ERW siting analysis (plan F4).

Every number the calculation uses lives in ``config/erw_siting/parameters/*.yaml``, one file per
group, with this schema per parameter::

    id, name, value, unit, distribution {type, params}, range [min, max],
    source {citation, doi_or_url, locator}, quality, status (ok | missing), notes

Rules enforced by :func:`validate` (decision D-48):
- ``status: ok`` requires a value, a unit, and a source with citation and DOI/URL;
- ``status: missing`` must have no value (nothing invented);
- a range, when given, must contain the value; a distribution must be of a known type;
- ids are unique across all files.
"""

from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from mrv_lab import io

STATUSES = ("ok", "missing")
QUALITIES = ("primary", "secondary", "literature", "definition", None)
DISTRIBUTIONS = ("fixed", "uniform", "triangular", "normal", "lognormal")


def parameters_dir() -> Path:
    """``config/erw_siting/parameters/``."""
    return io.repo_root() / "config" / "erw_siting" / "parameters"


def load(directory: Path | None = None) -> pd.DataFrame:
    """All parameters as a table (one row per parameter, with its ``group`` and ``file``)."""
    directory = directory or parameters_dir()
    rows: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.yaml")):
        content = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for param in content.get("parameters", []):
            rows.append({"group": content.get("group"), "file": path.name, **param})
    table = pd.DataFrame(rows)
    # pandas turns None into NaN in columns that also hold numbers; keep None (= empty in YAML).
    return table.astype(object).where(table.notna(), None)


def validate(table: pd.DataFrame) -> list[str]:
    """Return a list of problems (empty list = registry valid)."""
    problems: list[str] = []
    duplicated = table["id"][table["id"].duplicated()].tolist()
    problems += [f"duplicate id {d}" for d in duplicated]
    for p in table.to_dict("records"):
        pid = p["id"]
        if p.get("status") not in STATUSES:
            problems.append(f"{pid}: status must be one of {STATUSES}")
            continue
        if not p.get("unit"):
            problems.append(f"{pid}: unit is required")
        if p.get("quality") not in QUALITIES:
            problems.append(f"{pid}: quality must be one of {QUALITIES}")
        value = p.get("value")
        if p["status"] == "missing":
            if value is not None:
                problems.append(f"{pid}: missing parameters must not carry a value")
            continue
        if value is None:
            problems.append(f"{pid}: status ok requires a value")
        source = p.get("source") or {}
        if not source.get("citation") or not source.get("doi_or_url"):
            problems.append(f"{pid}: status ok requires source.citation and source.doi_or_url")
        rng = p.get("range")
        if rng is not None and value is not None and not (rng[0] <= value <= rng[1]):
            problems.append(f"{pid}: value {value} outside range {rng}")
        dist = p.get("distribution")
        if dist is not None and dist.get("type") not in DISTRIBUTIONS:
            problems.append(f"{pid}: distribution type must be one of {DISTRIBUTIONS}")
    return problems


def missing(table: pd.DataFrame) -> pd.DataFrame:
    """Parameters still without a verified value (listed in the README)."""
    return table.loc[table["status"] == "missing", ["group", "id", "name", "unit"]]


def value(table: pd.DataFrame, parameter_id: str) -> float:
    """Value of one ``ok`` parameter; raises if missing (no silent defaults)."""
    row = table.loc[table["id"] == parameter_id]
    if row.empty:
        raise KeyError(parameter_id)
    if row.iloc[0]["status"] != "ok":
        raise ValueError(f"{parameter_id} is missing: no verified value yet")
    return float(row.iloc[0]["value"])
