"""Soil properties from ISRIC SoilGrids 2.0 for the pilot departments (plan §5.2, F1 step 4).

Source: ISRIC SoilGrids 2.0, 250 m, CC BY 4.0 (data/SOURCES.md row D8). Cite Poggio et al. 2021,
doi:10.5194/soil-7-217-2021. SoilGrids values are model predictions, not measurements (gap G-01).

Decisions (journal, F1 step 4):
- variables: pH (water), CEC, clay, soil organic carbon, bulk density;
- depth 0-30 cm = thickness-weighted mean of the 0-5, 5-15 and 15-30 cm layers;
- statistics: mean, Q0.05 and Q0.95. The 0-30 cm quantiles are the thickness-weighted mean of the
  layer quantiles: an approximation, not the quantile of the 0-30 cm average.

Raw data: a window around each department is read from the native SoilGrids VRT (Interrupted Goode
Homolosine, 250 m, nodata -32768) and stored as GeoTIFF in ``data/raw/soilgrids/``, SHA-256 pinned.
Processing: depth aggregation, conversion to conventional units, reprojection to EPSG:9377 (250 m,
bilinear) and masking to the department outline; results in ``data/interim/erw_siting/soil/``.
"""

import time
from collections.abc import Callable
from pathlib import Path

import geopandas as gpd
import matplotlib
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import geometry_mask
from rasterio.warp import Resampling, calculate_default_transform, reproject, transform_bounds
from rasterio.windows import from_bounds

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from mrv_lab import io  # noqa: E402
from mrv_lab.erw_siting.regions import WORK_CRS  # noqa: E402

#: Native SoilGrids layer (virtual raster over cloud-optimised tiles).
VRT_URL = "https://files.isric.org/soilgrids/latest/data/{var}/{var}_{depth}_{stat}.vrt"

#: Variable -> (mapped units, conversion factor, conventional units). ISRIC SoilGrids FAQ,
#: "SoilGrids layers" (docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_01.html), checked
#: 2026-11-13: conventional value = mapped value / factor.
VARIABLES: dict[str, tuple[str, int, str]] = {
    "phh2o": ("pH x 10", 10, "pH"),
    "cec": ("mmol(c)/kg", 10, "cmol(c)/kg"),
    "clay": ("g/kg", 10, "%"),
    "soc": ("dg/kg", 10, "g/kg"),
    "bdod": ("cg/cm3", 100, "kg/dm3"),
}

#: Depth layer -> thickness in cm (0-30 cm aggregate).
DEPTHS: dict[str, int] = {"0-5cm": 5, "5-15cm": 10, "15-30cm": 15}

STATS: tuple[str, ...] = ("mean", "Q0.05", "Q0.95")

#: Output resolution in metres (same as SoilGrids).
RESOLUTION_M = 250.0

#: Margin added around each department window, in metres of the native CRS.
PAD_M = 1_000.0

#: Retries for remote reads: files.isric.org resets connections intermittently (seen 2026-11-13).
RETRY_DELAYS_S: tuple[float, ...] = (5, 15, 30, 60)

#: GDAL HTTP settings for /vsicurl reads (retries at block level, longer timeouts).
GDAL_HTTP_ENV = {"GDAL_HTTP_MAX_RETRY": 5, "GDAL_HTTP_RETRY_DELAY": 5, "GDAL_HTTP_TIMEOUT": 120}

Key = tuple[str, str, str]  # (department, variable, statistic)


def with_retries[T](
    func: Callable[[], T],
    delays_s: tuple[float, ...] = RETRY_DELAYS_S,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Call ``func``; on ``RasterioIOError`` wait and retry once per delay, then re-raise."""
    for delay in delays_s:
        try:
            return func()
        except rasterio.errors.RasterioIOError:
            sleep(delay)
    return func()


def layer_url(var: str, depth: str, stat: str) -> str:
    """URL of one native SoilGrids layer."""
    return VRT_URL.format(var=var, depth=depth, stat=stat)


def fetch_soilgrids(
    pilot: gpd.GeoDataFrame,
    raw_dir: Path | None = None,
) -> dict[tuple[str, str, str, str], Path]:
    """Read a window per department from every layer; store as GeoTIFF, SHA-256 pinned.

    Returns ``{(department, variable, depth, statistic): path}``. Existing files are not re-read,
    only re-checked against the registry.
    """
    raw_dir = raw_dir or io.raw_dir() / "soilgrids"
    paths: dict[tuple[str, str, str, str], Path] = {}
    with rasterio.Env(**GDAL_HTTP_ENV):
        for var in VARIABLES:
            for depth in DEPTHS:
                for stat in STATS:
                    url = layer_url(var, depth, stat)
                    for _, dept in pilot.iterrows():
                        name = dept["name"]
                        dest = raw_dir / name.replace(" ", "_") / f"{var}_{depth}_{stat}.tif"
                        if not dest.exists():
                            bounds, crs = dept.geometry.bounds, pilot.crs
                            with_retries(
                                lambda u=url, b=bounds, c=crs, d=dest: _fetch_window(u, c, b, d)
                            )
                        io.register_checksum(dest, f"{url} (window around {name})")
                        paths[(name, var, depth, stat)] = dest
    return paths


def _fetch_window(url: str, bounds_crs, bounds: tuple[float, ...], dest: Path) -> None:  # noqa: ANN001
    """Open the layer fresh (a failed read can leave a broken handle) and write one window."""
    with rasterio.open(f"/vsicurl/{url}") as src:
        _write_window(src, bounds_crs, bounds, dest)


def _write_window(src, bounds_crs, bounds: tuple[float, ...], dest: Path) -> None:  # noqa: ANN001
    left, bottom, right, top = transform_bounds(bounds_crs, src.crs, *bounds)
    window = from_bounds(
        left - PAD_M, bottom - PAD_M, right + PAD_M, top + PAD_M, transform=src.transform
    )
    window = window.round_offsets().round_lengths()
    data = src.read(1, window=window)
    profile = {
        "driver": "GTiff",
        "dtype": data.dtype,
        "count": 1,
        "height": data.shape[0],
        "width": data.shape[1],
        "crs": src.crs,
        "transform": src.window_transform(window),
        "nodata": src.nodata,
        "compress": "deflate",
    }
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    with rasterio.open(part, "w", **profile) as out:
        out.write(data, 1)
    part.replace(dest)


def depth_weighted(layers: list[np.ndarray], thickness_cm: list[int], nodata: float) -> np.ndarray:
    """Thickness-weighted mean of depth layers; NaN where any layer is ``nodata``."""
    stack = np.stack([layer.astype("float64") for layer in layers])
    stack[stack == nodata] = np.nan
    weights = np.asarray(thickness_cm, dtype="float64")[:, None, None]
    return (stack * weights).sum(axis=0) / weights.sum()


def to_work_grid(
    data: np.ndarray,
    src_transform: rasterio.Affine,
    src_crs: rasterio.crs.CRS,
    outline: gpd.GeoSeries,
) -> tuple[np.ndarray, rasterio.Affine]:
    """Reproject to WORK_CRS at RESOLUTION_M (bilinear) and set NaN outside ``outline``."""
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
    out = np.full((dst_height, dst_width), np.nan, dtype="float32")
    reproject(
        source=data.astype("float32"),
        destination=out,
        src_transform=src_transform,
        src_crs=src_crs,
        src_nodata=np.nan,
        dst_transform=dst_transform,
        dst_crs=WORK_CRS,
        dst_nodata=np.nan,
        resampling=Resampling.bilinear,
    )
    outside = geometry_mask(
        outline.to_crs(WORK_CRS).geometry, out_shape=out.shape, transform=dst_transform
    )
    out[outside] = np.nan
    return out, dst_transform


def process_soil(
    raw: dict[tuple[str, str, str, str], Path],
    pilot: gpd.GeoDataFrame,
    out_dir: Path | None = None,
) -> dict[Key, Path]:
    """Aggregate 0-30 cm, convert units, reproject and mask; write one float32 GeoTIFF per key."""
    out_dir = out_dir or io.interim_dir() / "erw_siting" / "soil"
    outputs: dict[Key, Path] = {}
    for _, dept in pilot.iterrows():
        name = dept["name"]
        outline = gpd.GeoSeries([dept.geometry], crs=pilot.crs)
        for var, (_, factor, _) in VARIABLES.items():
            for stat in STATS:
                layers, src_transform, src_crs, nodata = [], None, None, None
                for depth in DEPTHS:
                    with rasterio.open(raw[(name, var, depth, stat)]) as src:
                        layers.append(src.read(1))
                        src_transform, src_crs, nodata = src.transform, src.crs, src.nodata
                value = depth_weighted(layers, list(DEPTHS.values()), nodata) / factor
                grid, transform = to_work_grid(value, src_transform, src_crs, outline)
                dest = out_dir / name.replace(" ", "_") / f"{var}_0-30cm_{stat}.tif"
                dest.parent.mkdir(parents=True, exist_ok=True)
                profile = {
                    "driver": "GTiff",
                    "dtype": "float32",
                    "count": 1,
                    "height": grid.shape[0],
                    "width": grid.shape[1],
                    "crs": WORK_CRS,
                    "transform": transform,
                    "nodata": np.nan,
                    "compress": "deflate",
                }
                with rasterio.open(dest, "w", **profile) as out:
                    out.write(grid, 1)
                outputs[(name, var, stat)] = dest
    return outputs


def soil_summary(processed: dict[Key, Path]) -> pd.DataFrame:
    """Min / median / max and share of no-data pixels inside each department (QC only)."""
    rows = []
    for (name, var, stat), path in sorted(processed.items()):
        with rasterio.open(path) as src:
            grid = src.read(1)
        inside = grid[~np.isnan(grid)]
        rows.append(
            {
                "department": name,
                "variable": var,
                "unit": VARIABLES[var][2],
                "statistic": stat,
                "min": float(inside.min()) if inside.size else np.nan,
                "median": float(np.median(inside)) if inside.size else np.nan,
                "max": float(inside.max()) if inside.size else np.nan,
                "n_pixels": int(inside.size),
            }
        )
    return pd.DataFrame(rows)


def save_soil_qc(
    processed: dict[Key, Path],
    pilot: gpd.GeoDataFrame,
    out_dir: Path | None = None,
) -> tuple[list[Path], Path]:
    """One QC map per variable (0-30 cm mean, three departments) and a QC summary table."""
    out_dir = out_dir or io.interim_dir() / "erw_siting" / "qc"
    out_dir.mkdir(parents=True, exist_ok=True)
    pngs: list[Path] = []
    names = list(pilot["name"])
    for var, (_, _, unit) in VARIABLES.items():
        grids = []
        for name in names:
            with rasterio.open(processed[(name, var, "mean")]) as src:
                grids.append((src.read(1), src.bounds))
        values = np.concatenate([g[~np.isnan(g)] for g, _ in grids])
        vmin, vmax = np.percentile(values, [2, 98])
        fig, axes = plt.subplots(1, len(names), figsize=(4 * len(names), 4.5))
        for ax, name, (grid, b) in zip(axes, names, grids, strict=True):
            image = ax.imshow(
                grid,
                extent=(b.left, b.right, b.bottom, b.top),
                vmin=vmin,
                vmax=vmax,
                cmap="viridis",
            )
            ax.set_title(name, fontsize=9)
            ax.set_axis_off()
        fig.colorbar(image, ax=axes, shrink=0.7, label=f"{var} ({unit}), 0-30 cm mean")
        fig.suptitle(f"QC — SoilGrids {var}, 0-30 cm mean ({WORK_CRS})", fontsize=10)
        png = out_dir / f"soil_{var}_0-30cm_mean.png"
        fig.savefig(png, dpi=110, bbox_inches="tight")
        plt.close(fig)
        pngs.append(png)
    csv = out_dir / "soil_summary.csv"
    soil_summary(processed).round(3).to_csv(csv, index=False)
    return pngs, csv
