"""Terrain slope from the Copernicus DEM GLO-30 for the pilot departments (plan §5.5, filter 4).

Source: Copernicus DEM GLO-30 (Copernicus WorldDEM-30 licence: free reproduction, distribution and
adaptation; attribution notice required) — data/SOURCES.md row D11. The DEM is a surface model
(includes trees and buildings), so slope is noisy under forest; forests are excluded by land cover.

Decision (journal, F1 step 6a): slope is kept as a continuous percentage; the threshold (8 % or
12 %) is fixed in F5 with a cited source. The QC table reports the share of land in each band.

Method: 1°x1° tiles (EPSG:4326, ~30 m) are downloaded once and SHA-256 pinned; per department the
tiles are mosaicked, reprojected to EPSG:9377 at 30 m (bilinear), slope is computed with central
differences (``numpy.gradient``) as ``100 * sqrt(dz/dx² + dz/dy²)`` and masked to the outline.
"""

import math
import urllib.error
from pathlib import Path

import geopandas as gpd
import matplotlib
import numpy as np
import pandas as pd
import rasterio
from matplotlib.colors import ListedColormap
from rasterio.features import geometry_mask
from rasterio.merge import merge
from rasterio.warp import Resampling, calculate_default_transform, reproject, transform_bounds

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from mrv_lab import io, plotting  # noqa: E402
from mrv_lab.erw_siting.regions import WORK_CRS  # noqa: E402

#: Copernicus DEM GLO-30 public tiles on AWS (checked 2026-11-13). The name gives the tile's
#: south-west corner: N04_00_W074_00 covers 4-5° N, 74-73° W. Ocean tiles do not exist (HTTP 404).
TILE_URL = "https://copernicus-dem-30m.s3.amazonaws.com/{name}/{name}.tif"

RESOLUTION_M = 30.0

#: Slope bands reported in the QC table (percent); the filter threshold is chosen in F5.
SLOPE_BANDS_PCT: tuple[float, ...] = (8.0, 12.0)

PAD_DEG = 0.01


def tile_name(lat_south: int, lon_west: int) -> str:
    """Tile name for the 1°x1° cell whose south-west corner is (lat_south, lon_west)."""
    ns = "N" if lat_south >= 0 else "S"
    ew = "E" if lon_west >= 0 else "W"
    return f"Copernicus_DSM_COG_10_{ns}{abs(lat_south):02d}_00_{ew}{abs(lon_west):03d}_00_DEM"


def tiles_for_bounds(bounds: tuple[float, float, float, float]) -> list[str]:
    """Names of every tile intersecting ``(west, south, east, north)`` in degrees."""
    west, south, east, north = bounds
    return [
        tile_name(lat, lon)
        for lat in range(math.floor(south), math.floor(north) + 1)
        for lon in range(math.floor(west), math.floor(east) + 1)
    ]


def _bounds_4326(geometry, crs) -> tuple[float, float, float, float]:  # noqa: ANN001
    west, south, east, north = transform_bounds(crs, "EPSG:4326", *geometry.bounds)
    return west - PAD_DEG, south - PAD_DEG, east + PAD_DEG, north + PAD_DEG


def fetch_dem(pilot: gpd.GeoDataFrame, raw_dir: Path | None = None) -> dict[str, Path]:
    """Download every land tile covering the pilot departments (SHA-256 pinned); skip ocean."""
    raw_dir = raw_dir or io.raw_dir() / "copernicus_dem"
    names = sorted(
        {n for g in pilot.geometry for n in tiles_for_bounds(_bounds_4326(g, pilot.crs))}
    )
    paths: dict[str, Path] = {}
    for name in names:
        try:
            paths[name] = io.download_file(
                TILE_URL.format(name=name), raw_dir / f"{name}.tif", timeout_s=600
            )
        except urllib.error.HTTPError as err:
            if err.code != 404:  # 404 = no tile (ocean); anything else is a real error
                raise
    return paths


def slope_percent(elevation_m: np.ndarray, pixel_m: float) -> np.ndarray:
    """Slope in percent from an elevation grid with square pixels of ``pixel_m`` metres."""
    dz_dy, dz_dx = np.gradient(elevation_m.astype("float64"), pixel_m, pixel_m)
    return (100.0 * np.hypot(dz_dx, dz_dy)).astype("float32")


def slope_for_department(
    tiles: dict[str, Path],
    geometry,
    crs,
    out_path: Path,  # noqa: ANN001
) -> Path:
    """Mosaic tiles, reproject to WORK_CRS (30 m, bilinear), compute slope, mask, write GeoTIFF."""
    bounds = _bounds_4326(geometry, crs)
    needed = [tiles[n] for n in tiles_for_bounds(bounds) if n in tiles]
    sources = [rasterio.open(p) for p in needed]
    try:
        mosaic, transform = merge(sources, bounds=bounds, nodata=np.nan, dtype="float32")
    finally:
        for src in sources:
            src.close()
    elevation = mosaic[0]
    height, width = elevation.shape
    dst_transform, dst_width, dst_height = calculate_default_transform(
        "EPSG:4326", WORK_CRS, width, height, *bounds, resolution=RESOLUTION_M
    )
    projected = np.full((dst_height, dst_width), np.nan, dtype="float32")
    reproject(
        source=elevation,
        destination=projected,
        src_transform=transform,
        src_crs="EPSG:4326",
        src_nodata=np.nan,
        dst_transform=dst_transform,
        dst_crs=WORK_CRS,
        dst_nodata=np.nan,
        resampling=Resampling.bilinear,
    )
    slope = slope_percent(projected, RESOLUTION_M)
    outline = gpd.GeoSeries([geometry], crs=crs).to_crs(WORK_CRS)
    slope[geometry_mask(outline.geometry, out_shape=slope.shape, transform=dst_transform)] = np.nan
    out_path.parent.mkdir(parents=True, exist_ok=True)
    profile = {
        "driver": "GTiff",
        "dtype": "float32",
        "count": 1,
        "height": dst_height,
        "width": dst_width,
        "crs": WORK_CRS,
        "transform": dst_transform,
        "nodata": np.nan,
        "compress": "deflate",
        "predictor": 3,
        "tiled": True,
    }
    with rasterio.open(out_path, "w", **profile) as out:
        out.write(slope, 1)
    return out_path


def slope_by_department(
    tiles: dict[str, Path], pilot: gpd.GeoDataFrame, out_dir: Path | None = None
) -> dict[str, Path]:
    """One slope GeoTIFF per pilot department."""
    out_dir = out_dir or io.interim_dir() / "erw_siting" / "slope"
    return {
        row["name"]: slope_for_department(
            tiles, row.geometry, pilot.crs, out_dir / f"{row['name'].replace(' ', '_')}.tif"
        )
        for _, row in pilot.iterrows()
    }


def band_shares(slope: np.ndarray, bands: tuple[float, ...] = SLOPE_BANDS_PCT) -> dict[str, float]:
    """Share (0-1) of valid pixels below, between and above the band limits, plus the median."""
    valid = slope[~np.isnan(slope)]
    edges = (0.0, *bands, math.inf)
    shares = {
        f"{lo:g}-{hi:g}%": float(((valid >= lo) & (valid < hi)).mean()) if valid.size else np.nan
        for lo, hi in zip(edges[:-1], edges[1:], strict=True)
    }
    shares["median_pct"] = float(np.median(valid)) if valid.size else np.nan
    return shares


def save_slope_qc(slopes: dict[str, Path], out_dir: Path | None = None) -> tuple[Path, Path]:
    """QC map (slope bands) and QC table (share of land per band, median slope)."""
    out_dir = out_dir or io.interim_dir() / "erw_siting" / "qc"
    out_dir.mkdir(parents=True, exist_ok=True)
    png, csv = out_dir / "slope_pilot.png", out_dir / "slope_pilot_bands.csv"
    rows = []
    names = list(slopes)
    colors = ["#FFFFFF", plotting.HIGHLIGHT, plotting.OKABE_ITO["yellow"], plotting.GREY]
    fig, axes = plt.subplots(1, len(names), figsize=(4 * len(names), 4.5))
    for ax, name in zip(np.atleast_1d(axes), names, strict=True):
        with rasterio.open(slopes[name]) as src:
            rows.append({"department": name, **band_shares(src.read(1))})
            preview = src.read(1, out_shape=(src.height // 10, src.width // 10))  # display only
            b = src.bounds
        view = np.digitize(preview, SLOPE_BANDS_PCT) + 1
        view[np.isnan(preview)] = 0
        ax.imshow(
            view,
            cmap=ListedColormap(colors),
            vmin=0,
            vmax=3,
            interpolation="nearest",
            extent=(b.left, b.right, b.bottom, b.top),
        )
        ax.set_title(name, fontsize=9)
        ax.set_axis_off()
    lo, hi = SLOPE_BANDS_PCT
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in colors[1:]]
    fig.legend(
        handles,
        [f"< {lo:g} %", f"{lo:g}–{hi:g} %", f"> {hi:g} %"],
        loc="lower center",
        ncol=3,
        fontsize=8,
    )
    fig.suptitle(f"QC — Copernicus DEM slope, pilot departments ({WORK_CRS})", fontsize=10)
    fig.savefig(png, dpi=110, bbox_inches="tight")
    plt.close(fig)
    pd.DataFrame(rows).round(3).to_csv(csv, index=False)
    return png, csv
