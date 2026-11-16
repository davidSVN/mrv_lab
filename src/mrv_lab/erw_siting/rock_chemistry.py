"""Whole-rock chemistry of suitable rocks, from published sample tables (plan F4, group rock).

Every value in ``config/erw_siting/parameters/rock.yaml`` is computed here from the source PDFs,
so the registry numbers are reproducible (decision D-49):

- **Basalt** — Kerr et al. 2002, JGR 107(B7):2140, Table 1: 19 lavas of the Caribbean-Colombian
  oceanic plateau, SW Colombia (Central Cordillera). Samples with MgO <= 12 wt% are basalts
  (the paper's high-MgO threshold); the rest are picrites (kept for F7 sensitivity only).
  Oxides are reported on a dry basis; converted to the rock as quarried with ``1 - LOI/100``.
- **Gabbro** — no open Colombian analyses found; proxy = the basalt set (the intrusive equivalent
  of the same magma). Flagged in the registry notes.
- **Ultramafic** — García-Casco et al. 2020 (SGC, The Geology of Colombia vol. 2), Table 1:
  49 samples of the Medellín Metaharzburgitic Unit, already reported with LOI included.

Statistics per oxide: median (registry value), min and max (range); distribution triangular
(min, median, max). Only these aggregates are committed; the sample tables stay in ``data/raw``
because redistribution of the source tables is unclear (decision D-49).

Requires the ``pdftotext`` command (poppler-utils) to read the PDFs.
"""

import re
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

from mrv_lab import io

OXIDES = ("CaO", "MgO", "Na2O", "K2O")
#: MgO (wt%) above which Kerr et al. (2002) call a lava high-MgO / picritic.
PICRITE_MGO_WT_PCT = 12.0

KERR_2002_URL = "https://ir.library.oregonstate.edu/downloads/sj139345x"
GARCIA_CASCO_2020_URL = "https://www2.sgc.gov.co/LibroGeologiaColombia/tgc/sgcpubesp36201902.pdf"

SOURCES = {
    "kerr2002": {
        "citation": (
            "Kerr, A.C., Tarney, J., Kempton, P.D., Spadea, P., Nivia, A., Marriner, G.F. & "
            "Duncan, R.A. (2002). Pervasive mantle plume head heterogeneity: Evidence from the "
            "late Cretaceous Caribbean-Colombian oceanic plateau. Journal of Geophysical "
            "Research 107(B7), 2140"
        ),
        "doi_or_url": "doi:10.1029/2001JB000790",
        "locator": "Table 1 (major elements, wt%, dry basis; LOI row)",
    },
    "garcia_casco2020": {
        "citation": (
            "Garcia-Casco, A., Restrepo, J.J., Correa-Martinez, A.M., Blanco-Quintero, I.F., "
            "Proenza, J.A., Weber, M. & Butjosa, L. (2020). The petrologic nature of the "
            "'Medellin Dunite' revisited. In: Gomez, J. & Pinilla-Pachon, A.O. (eds.), The "
            "Geology of Colombia, Volume 2 Mesozoic. Servicio Geologico Colombiano, "
            "Publicaciones Geologicas Especiales 36"
        ),
        "doi_or_url": "doi:10.32685/pub.esp.36.2019.02",
        "locator": "Table 1 (whole-rock composition, wt%, LOI included)",
    },
}


def download() -> dict[str, Path]:
    """Download both source PDFs to ``data/raw/rock_chemistry/`` (SHA-256 pinned)."""
    folder = io.raw_dir() / "rock_chemistry"
    return {
        "kerr2002": io.download_file(KERR_2002_URL, folder / "kerr2002_jgr.pdf"),
        "garcia_casco2020": io.download_file(
            GARCIA_CASCO_2020_URL, folder / "garcia_casco2020_sgc.pdf"
        ),
    }


def pdf_text(path: Path) -> str:
    """Text of a PDF with its layout kept (``pdftotext -layout``)."""
    result = subprocess.run(
        ["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True, check=True
    )
    return result.stdout


def parse_kerr2002(text: str) -> pd.DataFrame:
    """Kerr et al. 2002 Table 1: one row per sample, oxides (wt%, dry) and LOI (wt%)."""
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("Table 1. Representative"))
    samples = lines[start + 2].split()
    wanted = ("Locality", *OXIDES, "LOI")
    rows: dict[str, list[str]] = {}
    for line in lines[start + 3 : start + 20]:
        parts = line.split()
        if parts and parts[0] in wanted:
            rows[parts[0]] = parts[1:]
    table = pd.DataFrame({k: rows[k] for k in wanted}, index=pd.Index(samples, name="sample"))
    for col in (*OXIDES, "LOI"):
        table[col] = table[col].astype(float)
    return table


def parse_garcia_casco2020(text: str) -> pd.DataFrame:
    """García-Casco et al. 2020 Table 1: one row per sample, oxides and LOI (wt%).

    Blank cells (not analysed) become NaN: each number is assigned to the header column whose
    centre is nearest to the number's centre in the fixed-width layout.
    """
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("Table 1. Whole"))
    header = next(line for line in lines[start + 1 : start + 4] if "SiO2" in line)
    names = [m.group().rstrip("*") for m in re.finditer(r"\S+", header)][1:-1]  # no Sample/Pub.
    centres = [(m.start() + m.end()) / 2 for m in re.finditer(r"\S+", header)][1:-1]
    records = []
    for line in lines[lines.index(header) + 1 :]:
        if line.startswith("Source:"):
            break
        if not line.strip():
            continue
        record: dict[str, float | str] = {"sample": line[:17].strip()}
        for m in re.finditer(r"\d+\.\d+", line):
            centre = (m.start() + m.end()) / 2
            col = names[int(np.argmin([abs(centre - c) for c in centres]))]
            record[col] = float(m.group())
        records.append(record)
    return pd.DataFrame(records).set_index("sample")


def as_quarried(table: pd.DataFrame) -> pd.DataFrame:
    """Dry-basis oxides -> wt% of the rock as quarried (volatiles included): ``x (1 - LOI/100)``."""
    out = table.copy()
    out[list(OXIDES)] = table[list(OXIDES)].mul(1 - table["LOI"] / 100, axis=0)
    return out


def sample_sets(texts: dict[str, str]) -> dict[str, pd.DataFrame]:
    """Rock sample sets (wt% as quarried): basalt, picrite, ultramafic."""
    kerr = as_quarried(parse_kerr2002(texts["kerr2002"]))
    return {
        "basalt": kerr[kerr["MgO"] <= PICRITE_MGO_WT_PCT],
        "picrite": kerr[kerr["MgO"] > PICRITE_MGO_WT_PCT],
        "ultramafic": parse_garcia_casco2020(texts["garcia_casco2020"]),
    }


def summarise(samples: pd.DataFrame) -> pd.DataFrame:
    """min, median, max and n per oxide (wt%), rounded to the sources' 2 decimals."""
    stats = samples[list(OXIDES)].agg(["min", "median", "max"]).round(2)
    return pd.concat([stats, samples[list(OXIDES)].count().rename("n").to_frame().T])


def registry_values(texts: dict[str, str]) -> dict[str, dict]:
    """Expected ``value``, ``range`` and ``distribution`` of every rock-group parameter."""
    sets = sample_sets(texts)
    rock_from = {"basalt": "basalt", "gabbro": "basalt", "ultramafic": "ultramafic"}
    out: dict[str, dict] = {}
    for rock, set_name in rock_from.items():
        stats = summarise(sets[set_name])
        for oxide in OXIDES:
            lo, mid, hi = (float(stats.loc[s, oxide]) for s in ("min", "median", "max"))
            out[f"{oxide.lower()}_wt_pct_{rock}"] = {
                "value": mid,
                "range": [lo, hi],
                "distribution": {
                    "type": "triangular",
                    "params": {"min": lo, "mode": mid, "max": hi},
                },
                "n": int(stats.loc["n", oxide]),
            }
    return out


def check_registry(table: pd.DataFrame, expected: dict[str, dict]) -> list[str]:
    """Differences between the registry and the values recomputed from the sources."""
    problems = []
    for pid, exp in expected.items():
        row = table.loc[table["id"] == pid]
        if row.empty:
            problems.append(f"{pid}: not in registry")
            continue
        p = row.iloc[0]
        if p["value"] != exp["value"] or list(p["range"]) != exp["range"]:
            problems.append(f"{pid}: registry {p['value']} {p['range']} != computed {exp}")
    return problems
