"""Current land cover from MapBiomas Colombia (Collection 3.0, 2024) for the pilot departments.

Plan §5.5, hard filter 2: where agriculture or livestock actually happens today (the UPRA frontier
says where it is allowed). Source: MapBiomas Colombia, CC BY 4.0 (data/SOURCES.md row D6).

Decisions (journal, F1 step 5):
- agricultural use = classes 21 (mosaic of agriculture and pasture), 35 (palm oil) and
  74 (banana, beta); forest plantation (9) is excluded. Every pixel keeps its class code.
- year 2024 only; multi-year stability is future work.

Collection 3.0 has no separate cropland class: crops and pasture share class 21 (gap G-09).
Categorical data: reprojection uses nearest neighbour, never averaging.
"""

from pathlib import Path

import geopandas as gpd
import matplotlib
import numpy as np
import pandas as pd
import rasterio
from matplotlib.colors import ListedColormap
from rasterio.features import geometry_mask
from rasterio.warp import Resampling, calculate_default_transform, reproject, transform_bounds
from rasterio.windows import from_bounds

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from mrv_lab import io, plotting  # noqa: E402
from mrv_lab.erw_siting.regions import WORK_CRS  # noqa: E402

YEAR = 2024

#: Official GeoTIFF linked from colombia.mapbiomas.org/descargas/mapas-de-las-colecciones/
#: (Google Drive file "INTEGRACION-COLOMBIA-COL3-2024.tif", 95,087,374 bytes; checked 2026-11-13).
MAPBIOMAS_URL = (
    "https://drive.usercontent.google.com/download"
    "?id=1eF0Pdj8HtKh3zvMULmOp1S-q-eFcpyd0&export=download&confirm=t"
)

#: Collection 3.0 legend (official "Código de la leyenda, Colección 3", checked 2026-11-13).
CLASSES: dict[int, str] = {
    1: "Forest formation",
    3: "Forest",
    5: "Mangrove",
    6: "Flooded forest",
    49: "Wooded sand vegetation",
    10: "Natural non forest formation",
    11: "Wetland",
    12: "Grasslands / herbaceous",
    32: "Hypersaline tidal flat",
    29: "Rocky outcrop",
    50: "Herbaceous sand vegetation",
    13: "Other non forest formation",
    81: "Andean herbaceous and shrubby vegetation",
    82: "Flooded Andean herbaceous and shrubby vegetation",
    14: "Agricultural and livestock area",
    9: "Forest plantation",
    35: "Palm oil",
    74: "Banana (beta)",
    21: "Mosaic of agriculture and pasture",
    22: "Non-vegetated area",
    23: "Beach, dune and sand spot",
    24: "Infrastructure",
    30: "Mining",
    68: "Other natural non-vegetated area",
    25: "Other non-vegetated area",
    75: "Solar panel farm",
    26: "Water body",
    33: "River, lake or ocean",
    31: "Aquaculture",
    34: "Glacier",
    27: "Not observed",
}

#: Classes counted as current agricultural use (decision D-31).
AGRO_CLASSES: tuple[int, ...] = (21, 35, 74)

#: Output resolution in metres (MapBiomas native ~30 m).
RESOLUTION_M = 30.0

#: Value written outside the department outline and where the source has no class.
NODATA = 0

PAD_M = 1_000.0


def fetch_land_cover() -> Path:
    """Download the 2024 national map once (SHA-256 pinned) and return its path."""
    dest = io.raw_dir() / "mapbiomas" / f"INTEGRACION-COLOMBIA-COL3-{YEAR}.tif"
    return io.download_file(MAPBIOMAS_URL, dest, timeout_s=600)


def to_work_grid(
    data: np.ndarray,
    src_transform: rasterio.Affine,
    src_crs: rasterio.crs.CRS,
    outline: gpd.GeoSeries,
) -> tuple[np.ndarray, rasterio.Affine]:
    """Reproject classes to WORK_CRS (nearest, RESOLUTION_M); NODATA outside ``outline``."""
    height, width = data.shape
    left, top = src_transform @ (0, 0)
    right, bottom = src_transform @ (width, height)
    dst_transform, dst_width, dst_height = calculate_default_transform(
        src_crs,
        WORK_CRS,
        width,
        height,
        left=left,
        bottom=bottom,
        right=right,
        top=top,
        resolution=RESOLUTION_M,
    )
    out = np.full((dst_height, dst_width), NODATA, dtype="uint8")
    reproject(
        source=data.astype("uint8"),
        destination=out,
        src_transform=src_transform,
        src_crs=src_crs,
        src_nodata=NODATA,
        dst_transform=dst_transform,
        dst_crs=WORK_CRS,
        dst_nodata=NODATA,
        resampling=Resampling.nearest,
    )
    outside = geometry_mask(
        outline.to_crs(WORK_CRS).geometry, out_shape=out.shape, transform=dst_transform
    )
    out[outside] = NODATA
    return out, dst_transform


def clip_land_cover(
    path: Path, pilot: gpd.GeoDataFrame, out_dir: Path | None = None
) -> dict[str, Path]:
    """Clip, reproject and mask the national map per department; one uint8 GeoTIFF each."""
    out_dir = out_dir or io.interim_dir() / "erw_siting" / "land_cover"
    out_dir.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, Path] = {}
    with rasterio.open(path) as src:
        for _, dept in pilot.iterrows():
            left, bottom, right, top = transform_bounds(pilot.crs, src.crs, *dept.geometry.bounds)
            pad = PAD_M / 111_000 if src.crs.is_geographic else PAD_M
            window = from_bounds(left - pad, bottom - pad, right + pad, top + pad, src.transform)
            window = window.round_offsets().round_lengths()
            data = src.read(1, window=window)
            outline = gpd.GeoSeries([dept.geometry], crs=pilot.crs)
            grid, transform = to_work_grid(data, src.window_transform(window), src.crs, outline)
            dest = out_dir / f"{dept['name'].replace(' ', '_')}_{YEAR}.tif"
            profile = {
                "driver": "GTiff",
                "dtype": "uint8",
                "count": 1,
                "height": grid.shape[0],
                "width": grid.shape[1],
                "crs": WORK_CRS,
                "transform": transform,
                "nodata": NODATA,
                "compress": "deflate",
            }
            with rasterio.open(dest, "w", **profile) as out:
                out.write(grid, 1)
            outputs[dept["name"]] = dest
    return outputs


def class_areas(grid: np.ndarray, pixel_area_m2: float) -> pd.DataFrame:
    """Hectares per class in a class grid (NODATA ignored)."""
    codes, counts = np.unique(grid[grid != NODATA], return_counts=True)
    return pd.DataFrame(
        {
            "class_id": codes.astype(int),
            "class_name": [CLASSES.get(int(c), "Unknown") for c in codes],
            "agricultural_use": [int(c) in AGRO_CLASSES for c in codes],
            "area_ha": counts * pixel_area_m2 / 10_000,
        }
    )


def land_cover_summary(clipped: dict[str, Path]) -> pd.DataFrame:
    """Hectares by department x class, largest first (QC only)."""
    tables = []
    for name, path in clipped.items():
        with rasterio.open(path) as src:
            table = class_areas(src.read(1), abs(src.transform.a * src.transform.e))
        tables.append(table.assign(department=name))
    summary = pd.concat(tables, ignore_index=True)
    summary = summary[["department", "class_id", "class_name", "agricultural_use", "area_ha"]]
    return summary.sort_values(["department", "area_ha"], ascending=[True, False]).reset_index(
        drop=True
    )


def save_land_cover_qc(clipped: dict[str, Path], out_dir: Path | None = None) -> tuple[Path, Path]:
    """QC map (agricultural classes highlighted, rest grey) and QC table by class."""
    out_dir = out_dir or io.interim_dir() / "erw_siting" / "qc"
    out_dir.mkdir(parents=True, exist_ok=True)
    png = out_dir / f"land_cover_{YEAR}_pilot.png"
    csv = out_dir / f"land_cover_{YEAR}_pilot_by_class.csv"
    land_cover_summary(clipped).round({"area_ha": 0}).to_csv(csv, index=False)

    # 0 = outside (white), 1 = other classes (grey), 2..4 = agricultural classes.
    colors = [
        "#FFFFFF",
        plotting.GREY,
        plotting.HIGHLIGHT,
        plotting.OKABE_ITO["orange"],
        plotting.OKABE_ITO["reddish_purple"],
    ]
    labels = ["Other classes", *(CLASSES[c] for c in AGRO_CLASSES)]
    names = list(clipped)
    fig, axes = plt.subplots(1, len(names), figsize=(4 * len(names), 4.5))
    for ax, name in zip(np.atleast_1d(axes), names, strict=True):
        with rasterio.open(clipped[name]) as src:
            grid = src.read(1, out_shape=(src.height // 10, src.width // 10))  # preview only
            b = src.bounds
        view = np.where(grid == NODATA, 0, 1)
        for i, code in enumerate(AGRO_CLASSES, start=2):
            view[grid == code] = i
        ax.imshow(
            view,
            cmap=ListedColormap(colors),
            vmin=0,
            vmax=4,
            interpolation="nearest",
            extent=(b.left, b.right, b.bottom, b.top),
        )
        ax.set_title(name, fontsize=9)
        ax.set_axis_off()
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in colors[1:]]
    fig.legend(handles, labels, loc="lower center", ncol=4, fontsize=8)
    fig.suptitle(f"QC — MapBiomas Colombia {YEAR}, agricultural classes ({WORK_CRS})", fontsize=10)
    fig.savefig(png, dpi=110, bbox_inches="tight")
    plt.close(fig)
    return png, csv
