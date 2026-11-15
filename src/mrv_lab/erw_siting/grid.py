"""1 km cell grid and per-cell filters and values (plan F5, parts 5.1-5.3).

The grid is a raster of 1 km pixels on EPSG:9377 aligned to whole kilometres; every pixel touching a
pilot department is a cell (``cell_id`` = ``E{x_km}_N{y_km}`` of its lower-left corner). A border
cell belongs to the department covering most of it (D-44).

Aggregation from source layers to cells:
- categorical masks (protected, frontier types, agricultural use): **fraction** of the cell, from
  100 m rasterisation (polygons) or the average of a 0/1 version of the 30 m class raster;
- slope: **median** of 30 m pixels and fraction above 8 % and 12 %;
- soil (250 m): **mean** of pixels; climate (5-10 km): bilinear value at the cell.
"""

from collections.abc import Callable
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import rasterize
from rasterio.transform import Affine
from rasterio.warp import Resampling, reproject
from shapely.geometry import box

from mrv_lab import io
from mrv_lab.erw_siting import climate, land_cover, soil
from mrv_lab.erw_siting.regions import WORK_CRS

CELL_M = 1_000
SUB = 10  # 100 m sub-pixels per cell side for polygon fractions


class Grid:
    """A 1 km raster grid covering ``bounds`` (metres, EPSG:9377), aligned to whole kilometres."""

    def __init__(self, bounds: tuple[float, float, float, float]):
        left, bottom, right, top = bounds
        self.x0 = np.floor(left / CELL_M) * CELL_M
        self.y1 = np.ceil(top / CELL_M) * CELL_M
        self.width = int(np.ceil((right - self.x0) / CELL_M))
        self.height = int(np.ceil((self.y1 - bottom) / CELL_M))
        self.transform = Affine(CELL_M, 0, self.x0, 0, -CELL_M, self.y1)

    @property
    def shape(self) -> tuple[int, int]:
        return self.height, self.width

    def cell_ids(self, rows: np.ndarray, cols: np.ndarray) -> list[str]:
        x_km = ((self.x0 + cols * CELL_M) / 1000).astype(int)
        y_km = ((self.y1 - (rows + 1) * CELL_M) / 1000).astype(int)
        return [f"E{x}_N{y}" for x, y in zip(x_km, y_km, strict=True)]

    def boxes(self, rows: np.ndarray, cols: np.ndarray) -> list:
        x = self.x0 + cols * CELL_M
        y = self.y1 - (rows + 1) * CELL_M
        return [box(a, b, a + CELL_M, b + CELL_M) for a, b in zip(x, y, strict=True)]


def polygon_fraction(grid: Grid, geometries: list) -> np.ndarray:
    """Fraction (0-1) of each cell covered by ``geometries`` (100 m rasterisation)."""
    if not geometries:
        return np.zeros(grid.shape)
    fine = rasterize(
        [(g, 1) for g in geometries],
        out_shape=(grid.height * SUB, grid.width * SUB),
        transform=grid.transform * Affine.scale(1 / SUB),
        fill=0,
        dtype="uint8",
    )
    return fine.reshape(grid.height, SUB, grid.width, SUB).mean(axis=(1, 3))


def raster_to_grid(
    paths: list[Path],
    grid: Grid,
    resampling: Resampling,
    transform_values: Callable[[np.ndarray], np.ndarray] | None = None,
) -> np.ndarray:
    """Resample one or more rasters (one per department) to the grid; first valid value wins."""
    out = np.full(grid.shape, np.nan, dtype="float32")
    for path in paths:
        with rasterio.open(path) as src:
            data = src.read(1).astype("float32")
            if src.nodata is not None and not np.isnan(src.nodata):
                data[data == src.nodata] = np.nan
            if transform_values is not None:
                data = transform_values(data)
            part = np.full(grid.shape, np.nan, dtype="float32")
            reproject(
                source=data,
                destination=part,
                src_transform=src.transform,
                src_crs=src.crs,
                src_nodata=np.nan,
                dst_transform=grid.transform,
                dst_crs=WORK_CRS,
                dst_nodata=np.nan,
                resampling=resampling,
            )
        out = np.where(np.isnan(out), part, out)
    return out


def build_cells(pilot: gpd.GeoDataFrame) -> tuple[Grid, gpd.GeoDataFrame, np.ndarray, np.ndarray]:
    """Cells of the pilot departments; returns grid, cells layer and their (rows, cols)."""
    grid = Grid(tuple(pilot.total_bounds))
    fractions = np.stack([polygon_fraction(grid, [g]) for g in pilot.geometry])
    total = fractions.sum(axis=0)
    rows, cols = np.nonzero(total > 0)
    best = fractions[:, rows, cols].argmax(axis=0)
    names = pilot["name"].to_numpy()
    x_center = grid.x0 + (cols + 0.5) * CELL_M
    y_center = grid.y1 - (rows + 0.5) * CELL_M
    cells = gpd.GeoDataFrame(
        {
            "cell_id": grid.cell_ids(rows, cols),
            "department": names[best],
            "x_center_m": x_center,
            "y_center_m": y_center,
            "area_in_department_km2": fractions[best, rows, cols],
        },
        geometry=grid.boxes(rows, cols),
        crs=WORK_CRS,
    )
    return grid, cells, rows, cols


def _dept_files(folder: Path, pattern: str, pilot: gpd.GeoDataFrame) -> list[Path]:
    return [folder / pattern.format(dept=n.replace(" ", "_")) for n in pilot["name"]]


def cell_filters(
    grid: Grid, rows: np.ndarray, cols: np.ndarray, pilot: gpd.GeoDataFrame, cell_ids: list[str]
) -> pd.DataFrame:
    """Per-cell filter fractions and slope statistics (raw slope, D-36)."""
    base = io.interim_dir() / "erw_siting"
    protected = gpd.read_file(base / "protected_areas_pilot.gpkg", layer="mask")
    frontier = gpd.read_file(base / "agricultural_frontier_pilot.gpkg", layer="mask")
    agro = list(land_cover.AGRO_CLASSES)

    def is_agro(a: np.ndarray) -> np.ndarray:
        return np.where(np.isnan(a) | (a == land_cover.NODATA), np.nan, np.isin(a, agro) * 1.0)

    slope_files = _dept_files(base / "slope", "{dept}.tif", pilot)
    layers = {
        "protected_frac": polygon_fraction(grid, list(protected.geometry)),
        "frontier_unconditioned_frac": polygon_fraction(
            grid, list(frontier[frontier["frontier_type"] == "No condicionada"].geometry)
        ),
        "frontier_conditioned_frac": polygon_fraction(
            grid, list(frontier[frontier["frontier_type"] == "Condicionada"].geometry)
        ),
        "agro_use_frac": raster_to_grid(
            _dept_files(base / "land_cover", f"{{dept}}_{land_cover.YEAR}.tif", pilot),
            grid,
            Resampling.average,
            is_agro,
        ),
        "slope_median_pct": raster_to_grid(slope_files, grid, Resampling.med),
        "slope_gt8_frac": raster_to_grid(
            slope_files,
            grid,
            Resampling.average,
            lambda a: np.where(np.isnan(a), np.nan, (a > 8) * 1.0),
        ),
        "slope_gt12_frac": raster_to_grid(
            slope_files,
            grid,
            Resampling.average,
            lambda a: np.where(np.isnan(a), np.nan, (a > 12) * 1.0),
        ),
    }
    table = pd.DataFrame({k: v[rows, cols] for k, v in layers.items()})
    table.insert(0, "cell_id", cell_ids)
    table["slope_smoothing_px"] = None
    return table


def cell_values(
    grid: Grid, rows: np.ndarray, cols: np.ndarray, pilot: gpd.GeoDataFrame, cell_ids: list[str]
) -> pd.DataFrame:
    """Long table: soil (mean of 250 m pixels) and climate (bilinear) per cell."""
    base = io.interim_dir() / "erw_siting"
    frames = []
    for var, (_, _, unit) in soil.VARIABLES.items():
        for stat in soil.STATS:
            files = _dept_files(base / "soil", f"{{dept}}/{var}_0-30cm_{stat}.tif", pilot)
            values = raster_to_grid(files, grid, Resampling.average)[rows, cols]
            frames.append(_long(cell_ids, "soil", var, stat, values, unit, "D8"))
    climate_sources = {
        "rain_annual_mm": "D9",
        "dry_months": "D9",
        "t2m_mean_c": "D10",
        "et_annual_mm": "D19",
    }
    for name, (unit, _) in climate.OUTPUTS.items():
        files = _dept_files(base / "climate", f"{{dept}}/{name}.tif", pilot)
        values = raster_to_grid(files, grid, Resampling.bilinear)[rows, cols]
        frames.append(_long(cell_ids, "climate", name, "mean", values, unit, climate_sources[name]))
    return pd.concat(frames, ignore_index=True)


def _long(ids, layer, variable, statistic, values, unit, source_id) -> pd.DataFrame:  # noqa: ANN001
    return pd.DataFrame(
        {
            "cell_id": ids,
            "layer": layer,
            "variable": variable,
            "statistic": statistic,
            "value": values,
            "unit": unit,
            "source_id": source_id,
        }
    )
