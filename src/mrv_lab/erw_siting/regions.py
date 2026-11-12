"""Pilot departments used to clip every layer in the vertical slice (plan §5.7).

Boundaries come from geoBoundaries gbOpen COL ADM1 (OpenStreetMap-derived, ODbL 1.0;
data/SOURCES.md row D17b). They are used only as a clipping mask: they are not the
official DANE limits, so no area-by-department figure is reported from them.
"""

import unicodedata
from pathlib import Path

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from mrv_lab import io, plotting  # noqa: E402

#: Working CRS for the whole analysis: MAGNA-SIRGAS / Origen-Nacional (metres).
WORK_CRS = "EPSG:9377"

#: Meta + the two Andean candidates; the Andean one is chosen in F2.
PILOT_DEPARTMENTS: tuple[str, ...] = ("Meta", "Tolima", "Valle del Cauca")

#: geoBoundaries COL ADM1, pinned to the full commit SHA so the file cannot change under us.
#: Direct Git LFS media URL (github.com/.../raw/... redirects here).
GEOBOUNDARIES_ADM1_URL = (
    "https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/"
    "9469f09592ced973a3448cf66b6100b741b64c0d/"
    "releaseData/gbOpen/COL/ADM1/geoBoundaries-COL-ADM1.geojson"
)

#: Column holding the department name in geoBoundaries files.
NAME_COLUMN = "shapeName"


def normalize_name(name: str) -> str:
    """Lower-case, strip accents, collapse spaces: ``"Del  Cáuca"`` -> ``"del cauca"``."""
    ascii_only = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    return " ".join(ascii_only.lower().split())


def fetch_departments() -> Path:
    """Download the geoBoundaries ADM1 file once (SHA-256 pinned) and return its path."""
    dest = io.raw_dir() / "geoboundaries" / "geoBoundaries-COL-ADM1.geojson"
    return io.download_file(GEOBOUNDARIES_ADM1_URL, dest)


def read_departments(path: Path, name_column: str = NAME_COLUMN) -> gpd.GeoDataFrame:
    """Read all departments, keep ``name`` + geometry, and reproject to :data:`WORK_CRS`."""
    gdf = gpd.read_file(path)
    gdf = gdf[[name_column, "geometry"]].rename(columns={name_column: "name"})
    return gdf.to_crs(WORK_CRS)


def select_pilot_departments(
    departments: gpd.GeoDataFrame,
    names: tuple[str, ...] = PILOT_DEPARTMENTS,
) -> gpd.GeoDataFrame:
    """Return rows of ``departments`` whose ``name`` matches ``names`` (ignoring case/accents).

    Raises:
        KeyError: if any requested name is missing; the message lists the names available.
    """
    keys = departments["name"].map(normalize_name)
    wanted = {normalize_name(n): n for n in names}
    missing = sorted(set(wanted) - set(keys))
    if missing:
        available = ", ".join(sorted(departments["name"]))
        raise KeyError(f"Departments not found: {missing}. Available: {available}")
    pilot = departments[keys.isin(wanted)].copy()
    pilot["name"] = pilot["name"].map(lambda n: wanted[normalize_name(n)])
    return pilot.sort_values("name").reset_index(drop=True)


def save_pilot_departments(
    pilot: gpd.GeoDataFrame,
    departments: gpd.GeoDataFrame,
    out_dir: Path | None = None,
) -> tuple[Path, Path]:
    """Write the pilot layer (GeoPackage) and an internal QC map (PNG); return both paths."""
    out_dir = out_dir or io.interim_dir() / "erw_siting"
    (out_dir / "qc").mkdir(parents=True, exist_ok=True)
    gpkg = out_dir / "pilot_departments.gpkg"
    png = out_dir / "qc" / "pilot_departments.png"

    pilot.to_file(gpkg, driver="GPKG")

    fig, ax = plt.subplots(figsize=(6, 7))
    departments.plot(ax=ax, color=plotting.GREY, edgecolor="white", linewidth=0.4)
    pilot.plot(ax=ax, color=plotting.HIGHLIGHT, edgecolor="white", linewidth=0.8)
    for _, row in pilot.iterrows():
        point = row.geometry.representative_point()
        ax.annotate(row["name"], (point.x, point.y), ha="center", fontsize=8, color="white")
    ax.set_title(f"QC — pilot departments ({WORK_CRS})", fontsize=10)
    ax.set_axis_off()
    fig.savefig(png, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return gpkg, png


def area_km2(gdf: gpd.GeoDataFrame) -> list[float]:
    """Return polygon areas in km² (``gdf`` must be in a metric CRS such as :data:`WORK_CRS`)."""
    return [round(a / 1e6, 0) for a in gdf.geometry.area]
