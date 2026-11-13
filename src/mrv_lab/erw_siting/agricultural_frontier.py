"""Agricultural frontier (UPRA) for the pilot departments (plan §5.5, hard filter 1).

Source: UPRA, "Frontera agrícola y frontera agrícola condicionada" (MADR Resolución 261 de 2018),
ArcGIS REST layer; CC BY-SA 4.0 under UPRA's open-data license (data/SOURCES.md row D4, D-10).

Both frontier types are kept and labelled (decision D-18): ``No condicionada`` (suitable for farming
by law) and ``Condicionada`` (farming may be permitted, restricted or prohibited by law). Which type
counts as candidate land is decided in F5, with numbers.

The layer is served in pages of at most ``PAGE_SIZE`` features. Each page is stored as its own file
and pinned by SHA-256 like any other download (rule R-03); the server returned byte-identical pages
on repeated requests (checked 2026-11-13).
"""

from pathlib import Path
from urllib.parse import urlencode

import geopandas as gpd
import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from mrv_lab import io, plotting  # noqa: E402
from mrv_lab.erw_siting.geometry import repair_polygons  # noqa: E402
from mrv_lab.erw_siting.regions import WORK_CRS  # noqa: E402

#: UPRA ArcGIS REST layer (verified 2026-11-13).
FRONTIER_LAYER_URL = (
    "https://geoservicios.upra.gov.co/arcgis/rest/services/ordenamiento_productivo/"
    "frontera_agricola_frontera_agricola_condicionada/MapServer/0"
)

#: DANE department codes of the pilot departments (field ``cod_depart`` in the layer).
PILOT_DANE_CODES: dict[str, str] = {"Meta": "50", "Tolima": "73", "Valle del Cauca": "76"}

#: Server limit (``maxRecordCount``) per request.
PAGE_SIZE = 2000

#: Layer field -> name used here.
COLUMNS = {
    "objectid": "objectid",
    "departamen": "department",
    "cod_dane_mpio": "municipality_code",
    "municipio": "municipality",
    "tipo_frontera": "frontier_type",
}

_M2_PER_HA = 10_000


def page_url(dane_code: str, offset: int, page_size: int = PAGE_SIZE) -> str:
    """Query URL for one page of one department, ordered by ``objectid``, as GeoJSON in WGS84."""
    params = {
        "where": f"cod_depart='{dane_code}'",
        "outFields": ",".join(COLUMNS),
        "orderByFields": "objectid",
        "resultOffset": offset,
        "resultRecordCount": page_size,
        "outSR": 4326,
        "f": "geojson",
    }
    return f"{FRONTIER_LAYER_URL}/query?{urlencode(params)}"


def _page_is_last(path: Path, page_size: int) -> bool:
    page = gpd.read_file(path)
    return len(page) < page_size


def fetch_frontier(
    dane_codes: dict[str, str] | None = None,
    page_size: int = PAGE_SIZE,
    raw_dir: Path | None = None,
) -> list[Path]:
    """Download every page for each department (each page SHA-256 pinned); return the page paths."""
    dane_codes = dane_codes or PILOT_DANE_CODES
    raw_dir = raw_dir or io.raw_dir() / "upra_frontier"
    paths: list[Path] = []
    for code in dane_codes.values():
        offset = 0
        while True:
            dest = raw_dir / f"frontier_{code}_{offset:06d}.geojson"
            path = io.download_file(page_url(code, offset, page_size), dest)
            paths.append(path)
            if _page_is_last(path, page_size):
                break
            offset += page_size
    return paths


def read_frontier(paths: list[Path]) -> gpd.GeoDataFrame:
    """Concatenate pages, drop duplicate ``objectid``, repair polygons, reproject to WORK_CRS."""
    pages = [gpd.read_file(p) for p in paths]
    gdf = gpd.GeoDataFrame(pd.concat(pages, ignore_index=True), crs=pages[0].crs)
    gdf = gdf[[*COLUMNS, "geometry"]].rename(columns=COLUMNS)
    gdf = gdf.drop_duplicates(subset="objectid")
    return repair_polygons(gdf).to_crs(WORK_CRS)


def frontier_mask(frontier: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Union per department x frontier type, with polygon count and area in hectares."""
    counts = frontier.groupby(["department", "frontier_type"]).size().rename("n_polygons")
    mask = frontier.dissolve(by=["department", "frontier_type"], as_index=False)
    mask = mask[["department", "frontier_type", "geometry"]].merge(
        counts.reset_index(), on=["department", "frontier_type"]
    )
    mask["area_ha"] = mask.geometry.area / _M2_PER_HA
    return mask


def save_frontier(
    mask: gpd.GeoDataFrame,
    pilot: gpd.GeoDataFrame,
    out_dir: Path | None = None,
) -> tuple[Path, Path, Path]:
    """Write the mask (GeoPackage), a QC map and a QC table (hectares by department x type)."""
    out_dir = out_dir or io.interim_dir() / "erw_siting"
    (out_dir / "qc").mkdir(parents=True, exist_ok=True)
    gpkg = out_dir / "agricultural_frontier_pilot.gpkg"
    png = out_dir / "qc" / "agricultural_frontier_pilot.png"
    csv = out_dir / "qc" / "agricultural_frontier_pilot_by_type.csv"

    mask.to_file(gpkg, layer="mask", driver="GPKG")
    table = mask.drop(columns="geometry").sort_values(["department", "frontier_type"])
    table.round({"area_ha": 0}).to_csv(csv, index=False)

    colors = {"No condicionada": plotting.HIGHLIGHT, "Condicionada": plotting.OKABE_ITO["orange"]}
    fig, ax = plt.subplots(figsize=(7, 6))
    pilot.plot(ax=ax, color=plotting.GREY, edgecolor="white", linewidth=0.8)
    for frontier_type, color in colors.items():
        part = mask[mask["frontier_type"] == frontier_type]
        if not part.empty:
            part.plot(ax=ax, color=color, edgecolor="none", label=frontier_type)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in colors.values()]
    ax.legend(handles, [f"Frontier: {t}" for t in colors], loc="lower left", fontsize=8)
    for _, row in pilot.iterrows():
        point = row.geometry.representative_point()
        ax.annotate(row["name"], (point.x, point.y), ha="center", fontsize=9)
    ax.set_title(f"QC — UPRA agricultural frontier in pilot departments ({WORK_CRS})", fontsize=10)
    ax.set_axis_off()
    fig.savefig(png, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return gpkg, png, csv
