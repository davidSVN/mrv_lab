"""Lithology: where suitable rock for ERW is, from the SGC geological map (plan F2).

Source: Servicio Geológico Colombiano, Mapa Geológico de Colombia 2023, 1:1,500,000 (data/SOURCES.md
row D1). Internal use only: derived tables, maps or numbers are not published (git, posts) until SGC
answers in writing (decision D-08). Raw and derived files stay in gitignored folders.

Every geological unit (layer ``UC``) is kept, not only candidates (decision D-39): each gets the
list of rock types named in its description (``rock_types``), so a future rock catalogue (F4) can
select units by rock type. A rule-based class is proposed and David reviews it by hand:

- **Apta**: a mafic or ultramafic rock is the unit's main rock (named first, not mixed);
- **Mixta**: mafic rock present but interbedded or mixed with other rocks in unknown proportion;
- **No apta**: no mafic rock, or only as a minor component ("algunos", "fragmentos de", ...).

Mixta units do not count as rock supply by default; they are flagged for a sensitivity scenario.
Ultramafic units are flagged for possible nickel / chromium content.
"""

import re
from pathlib import Path

import geopandas as gpd
import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from mrv_lab import io, plotting  # noqa: E402
from mrv_lab.erw_siting.regions import WORK_CRS  # noqa: E402

#: File GDB linked from https://www2.sgc.gov.co/MGC/Paginas/mgc_1_5M2023.aspx (checked 2026-11-13).
SGC_GDB_URL = "https://www2.sgc.gov.co/MGC/Documents/MGC_2023/mgc2023.gdb.zip"
UNITS_LAYER = "UC"

#: Canonical rock type -> regex on the (lower-case) Spanish description.
ROCK_TERMS: dict[str, str] = {
    # mafic
    "basalt": r"basalt",
    "basaltic andesite": r"andesitas? bas[aá]ltica",
    "gabbro": r"gabro|gabronorit",
    "diabase": r"diabas",
    "dolerite": r"dolerit",
    "norite": r"norit",
    "picrite": r"picrit",
    "tholeiite": r"toleit",
    # ultramafic
    "peridotite": r"peridotit",
    "dunite": r"dunit",
    "harzburgite": r"harzburgit",
    "lherzolite": r"lerzolit|lherzolit",
    "websterite": r"websterit",
    "pyroxenite": r"piroxenit",
    "serpentinite": r"serpentinit",
    # other igneous
    "andesite": r"andesit(?!as? bas[aá]ltica)",
    "dacite": r"dacit",
    "rhyolite": r"riolit",
    "granite": r"granit(?!oid)",
    "granitoid": r"granitoid",
    "granodiorite": r"granodiorit",
    "tonalite": r"tonalit",
    "diorite": r"(?<!grano)(?<!cuarzo)diorit",
    "tuff": r"\btoba",
    "ignimbrite": r"ignimbrit",
    # metamorphic
    "amphibolite": r"anfibolit",
    "gneiss": r"gneis",
    "schist": r"esquist",
    "phyllite": r"filit",
    "marble": r"m[aá]rmol",
    "quartzite": r"cuarcit",
    "migmatite": r"migmatit",
    "granulite": r"granulit",
    # sedimentary
    "limestone": r"caliza",
    "sandstone": r"arenit|arenisc",
    "mudstone": r"lodolit",
    "siltstone": r"limolit",
    "claystone": r"arcillolit",
    "shale": r"shale|lutit",
    "conglomerate": r"conglomerad",
    "chert": r"chert",
    "breccia": r"brecha",
    "unconsolidated deposits": r"dep[oó]sitos|aluvia|gravas|arenas",
}

MAFIC = frozenset(
    {
        "basalt",
        "basaltic andesite",
        "gabbro",
        "diabase",
        "dolerite",
        "norite",
        "picrite",
        "tholeiite",
    }
)
ULTRAMAFIC = frozenset(
    {
        "peridotite",
        "dunite",
        "harzburgite",
        "lherzolite",
        "websterite",
        "pyroxenite",
        "serpentinite",
    }
)
SUITABLE = MAFIC | ULTRAMAFIC

#: Phrases that mark the following rock as a minor component.
MINOR_CUES = (
    r"algun[oa]s",
    r"fragmentos de",
    r"variaciones a",
    r"espor[aá]dic",
    r"ricas? en fragmentos",
    r"l[ií]ticos de",
    r"lentes de",
    r"menores",
    r"ocasional",
)
#: Phrases that mark interbedding / mixing with other rocks.
MIX_CUES = (r"intercalad", r"interestratificad", r"asociad", r"mezcla", r"con niveles de")

CLASSES = ("Apta", "Mixta", "No apta")


def rock_types(description: str | float | None) -> list[str]:
    """Rock types named in a description, in order of first appearance."""
    text = description.lower() if isinstance(description, str) else ""
    found = []
    for name, pattern in ROCK_TERMS.items():
        match = re.search(pattern, text)
        if match:
            found.append((match.start(), name))
    return [name for _, name in sorted(found)]


def _is_minor(text: str, position: int) -> bool:
    window = text[max(0, position - 40) : position]
    return any(re.search(cue, window) for cue in MINOR_CUES)


def classify(description: str | float | None) -> tuple[str, str]:
    """Proposed class and reason for one unit description."""
    text = description.lower() if isinstance(description, str) else ""
    types = rock_types(description)
    suitable = [t for t in types if t in SUITABLE]
    if not suitable:
        return "No apta", "no mafic or ultramafic rock named"
    positions = {t: re.search(ROCK_TERMS[t], text).start() for t in suitable}
    major = [t for t in suitable if not _is_minor(text, positions[t])]
    if not major:
        return "No apta", f"only minor mention of {', '.join(suitable)}"
    others = [t for t in types if t not in SUITABLE and t != "unconsolidated deposits"]
    if types[0] in SUITABLE and not (others and any(re.search(c, text) for c in MIX_CUES)):
        return "Apta", f"main rock {types[0]}"
    if any(re.search(c, text) for c in MIX_CUES) or types[0] not in SUITABLE:
        return "Mixta", f"{', '.join(major)} with {', '.join(others) or 'other rocks'}"
    return "Apta", f"main rock {types[0]}"


def fetch_geology() -> Path:
    """Download the SGC File GDB once (SHA-256 pinned). Internal use only (D-08)."""
    return io.download_file(SGC_GDB_URL, io.raw_dir() / "sgc" / "mgc2023.gdb.zip", timeout_s=600)


def read_units(path: Path) -> gpd.GeoDataFrame:
    """Read the geological units layer and reproject to WORK_CRS."""
    gdf = gpd.read_file(f"zip://{path}", layer=UNITS_LAYER)
    gdf = gdf[["CodigoUC", "SimboloUC", "Descripcion", "Edad", "geometry"]].rename(
        columns={
            "CodigoUC": "unit_code",
            "SimboloUC": "symbol",
            "Descripcion": "description",
            "Edad": "age",
        }
    )
    gdf["unit_code"] = gdf["unit_code"].astype("Int64")
    return gdf.to_crs(WORK_CRS)


def unit_table(units: gpd.GeoDataFrame, pilot: gpd.GeoDataFrame) -> pd.DataFrame:
    """One row per unit: rock types, proposed class, areas in Colombia and in each pilot dept."""
    units = units.assign(area_km2=units.geometry.area / 1e6)
    table = units.groupby(
        ["unit_code", "symbol", "description", "age"], dropna=False, as_index=False
    ).agg(n_polygons=("geometry", "size"), area_km2_colombia=("area_km2", "sum"))
    table["rock_types"] = table["description"].map(lambda d: "; ".join(rock_types(d)))
    table["has_suitable_rock"] = table["description"].map(
        lambda d: any(t in SUITABLE for t in rock_types(d))
    )
    table["ultramafic"] = table["description"].map(
        lambda d: any(t in ULTRAMAFIC for t in rock_types(d))
    )
    proposed = table["description"].map(classify)
    table["proposed_class"] = [c for c, _ in proposed]
    table["reason"] = [r for _, r in proposed]
    for _, dept in pilot.iterrows():
        clipped = gpd.clip(units[["unit_code", "geometry"]], dept.geometry)
        area = clipped.geometry.area.groupby(clipped["unit_code"]).sum() / 1e6
        table[f"area_km2_{dept['name'].replace(' ', '_')}"] = (
            table["unit_code"].map(area).fillna(0.0)
        )
    return table.sort_values(["has_suitable_rock", "area_km2_colombia"], ascending=False)


def apply_review(table: pd.DataFrame, review_path: Path) -> pd.DataFrame:
    """Merge David's review; create the review template if it does not exist (never overwrite).

    The review file keeps one row per unit with ``review_class`` (Apta / Mixta / No apta, empty =
    accept the proposal) and ``review_note``. ``final_class`` = review if given, else proposal.
    """
    if not review_path.exists():
        review_path.parent.mkdir(parents=True, exist_ok=True)
        template = table[
            ["unit_code", "symbol", "description", "rock_types", "proposed_class", "reason"]
        ].assign(review_class="", review_note="")
        template.to_csv(review_path, index=False)
    review = pd.read_csv(review_path, dtype={"review_class": "string", "review_note": "string"})
    invalid = set(review["review_class"].dropna()) - set(CLASSES)
    if invalid:
        raise ValueError(f"Unknown review_class values {invalid}; use one of {CLASSES}")
    merged = table.merge(
        review[["unit_code", "review_class", "review_note"]], on="unit_code", how="left"
    )
    merged["final_class"] = merged["review_class"].fillna(merged["proposed_class"])
    merged["reviewed"] = merged["review_class"].notna()
    return merged


def classified_units(units: gpd.GeoDataFrame, table: pd.DataFrame) -> gpd.GeoDataFrame:
    """Unit polygons with their final class and flags."""
    cols = ["unit_code", "final_class", "rock_types", "ultramafic", "reviewed"]
    return units.merge(table[cols], on="unit_code", how="left")


def save_lithology(
    classified: gpd.GeoDataFrame,
    table: pd.DataFrame,
    departments: gpd.GeoDataFrame,
    pilot: gpd.GeoDataFrame,
    out_dir: Path | None = None,
) -> tuple[Path, Path, Path, Path]:
    """GeoPackage of classified units, unit table, QC map and QC table (all gitignored)."""
    out_dir = out_dir or io.interim_dir() / "erw_siting" / "geology"
    qc = io.interim_dir() / "erw_siting" / "qc"
    out_dir.mkdir(parents=True, exist_ok=True)
    qc.mkdir(parents=True, exist_ok=True)
    gpkg = out_dir / "geology_units_classified.gpkg"
    table_csv = out_dir / "lithology_units.csv"
    png = qc / "lithology_suitable_rock.png"
    qc_csv = qc / "lithology_area_by_class.csv"

    classified.to_file(gpkg, layer="units", driver="GPKG")
    table.to_csv(table_csv, index=False)
    area_cols = [c for c in table.columns if c.startswith("area_km2")]
    table.groupby("final_class")[area_cols].sum().round(0).to_csv(qc_csv)

    colors = {"Apta": plotting.HIGHLIGHT, "Mixta": plotting.OKABE_ITO["orange"]}
    fig, ax = plt.subplots(figsize=(6, 7))
    departments.plot(ax=ax, color="#EEEEEE", edgecolor="white", linewidth=0.4)
    for cls, color in colors.items():
        part = classified[classified["final_class"] == cls]
        if not part.empty:
            part.plot(ax=ax, color=color, edgecolor="none")
    ultra = classified[(classified["final_class"] == "Apta") & classified["ultramafic"]]
    if not ultra.empty:
        ultra.boundary.plot(ax=ax, color=plotting.OKABE_ITO["vermillion"], linewidth=0.6)
    pilot.boundary.plot(ax=ax, color="black", linewidth=0.8)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in colors.values()]
    handles.append(plt.Line2D([], [], color=plotting.OKABE_ITO["vermillion"]))
    handles.append(plt.Line2D([], [], color="black"))
    ax.legend(
        handles,
        ["Apta (suitable)", "Mixta (mixed)", "Ultramafic outline", "Pilot departments"],
        loc="lower left",
        fontsize=8,
    )
    ax.set_title(f"QC — SGC 2023 units by ERW suitability ({WORK_CRS}) — internal use", fontsize=9)
    ax.set_axis_off()
    fig.savefig(png, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return gpkg, table_csv, png, qc_csv
