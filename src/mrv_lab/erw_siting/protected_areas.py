"""Protected areas (RUNAP) as a hard exclusion mask for the pilot departments (plan §5.5).

Source: Registro Único Nacional de Áreas Protegidas, Parques Nacionales Naturales de Colombia,
CC BY-SA 4.0 (data/SOURCES.md row D18). Decisions (journal, F1 step 2):
1. every category is excluded (area per category is reported to judge their weight);
2. every condition (REGISTRADA / INSCRITA / CONSTRUCCION ...) is excluded;
3. the downloaded ``latest.zip`` is pinned by SHA-256; a new upstream version raises an error and is
   accepted deliberately.
"""

from pathlib import Path

import geopandas as gpd
import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from mrv_lab import io, plotting  # noqa: E402
from mrv_lab.erw_siting.geometry import repair_polygons  # noqa: E402
from mrv_lab.erw_siting.regions import WORK_CRS  # noqa: E402

#: Official download linked by the PNNC open-data portal; overwritten upstream on each update.
RUNAP_URL = "https://storage.googleapis.com/pnn_geodatabase/runap/latest.zip"

#: RUNAP shapefile column -> name used here.
COLUMNS = {"ap_nombre": "name", "ap_categor": "category", "condicion": "condition"}

_M2_PER_HA = 10_000


def fetch_runap() -> Path:
    """Download RUNAP once (SHA-256 pinned) and return the local zip path."""
    return io.download_file(RUNAP_URL, io.raw_dir() / "runap" / "runap_latest.zip")


def read_runap(path: Path) -> gpd.GeoDataFrame:
    """Read RUNAP: keep name/category/condition, repair polygons, reproject to WORK_CRS."""
    gdf = gpd.read_file(path)
    gdf = gdf[[*COLUMNS, "geometry"]].rename(columns=COLUMNS)
    return repair_polygons(gdf).to_crs(WORK_CRS)


def clip_to_pilot(areas: gpd.GeoDataFrame, pilot: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Intersect protected areas with the pilot departments; adds a ``department`` column.

    An area crossing a department border is split into one piece per department.
    """
    departments = pilot[["name", "geometry"]].rename(columns={"name": "department"})
    candidates = areas[areas.intersects(departments.union_all())]
    return gpd.overlay(candidates, departments, how="intersection", keep_geom_type=True)


def exclusion_mask(clipped: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Union of all protected areas per department (overlaps counted once)."""
    mask = clipped.dissolve(by="department", as_index=False)[["department", "geometry"]]
    mask["area_ha"] = mask.geometry.area / _M2_PER_HA
    return mask


def summary_table(clipped: gpd.GeoDataFrame) -> pd.DataFrame:
    """Areas and hectares by department x category x condition (QC only).

    Hectares are summed per row, so overlapping areas (e.g. a private reserve inside a district)
    are counted twice here; the exclusion mask counts them once.
    """
    table = clipped.assign(area_ha=clipped.geometry.area / _M2_PER_HA)
    return (
        table.groupby(["department", "category", "condition"], as_index=False)
        .agg(n_areas=("name", "size"), area_ha=("area_ha", "sum"))
        .sort_values(["department", "area_ha"], ascending=[True, False])
        .reset_index(drop=True)
    )


def save_protected_areas(
    clipped: gpd.GeoDataFrame,
    mask: gpd.GeoDataFrame,
    pilot: gpd.GeoDataFrame,
    out_dir: Path | None = None,
) -> tuple[Path, Path, Path]:
    """Write the layers (GeoPackage: ``areas`` + ``mask``), a QC map and a QC table."""
    out_dir = out_dir or io.interim_dir() / "erw_siting"
    (out_dir / "qc").mkdir(parents=True, exist_ok=True)
    gpkg = out_dir / "protected_areas_pilot.gpkg"
    png = out_dir / "qc" / "protected_areas_pilot.png"
    csv = out_dir / "qc" / "protected_areas_pilot_by_category.csv"

    clipped.to_file(gpkg, layer="areas", driver="GPKG")
    mask.to_file(gpkg, layer="mask", driver="GPKG")
    summary_table(clipped).round({"area_ha": 0}).to_csv(csv, index=False)

    fig, ax = plt.subplots(figsize=(7, 6))
    pilot.plot(ax=ax, color=plotting.GREY, edgecolor="white", linewidth=0.8)
    mask.plot(ax=ax, color=plotting.HIGHLIGHT, edgecolor="none")
    for _, row in pilot.iterrows():
        point = row.geometry.representative_point()
        ax.annotate(row["name"], (point.x, point.y), ha="center", fontsize=9)
    ax.set_title(f"QC — RUNAP protected areas in pilot departments ({WORK_CRS})", fontsize=10)
    ax.set_axis_off()
    fig.savefig(png, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return gpkg, png, csv
