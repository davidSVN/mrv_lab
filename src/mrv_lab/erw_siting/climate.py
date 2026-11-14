"""Climate normals 1991-2020 for the pilot departments (plan §5.2, F1 step 6b).

Rainfall (decision D-42): CHIRPS v2.0 monthly 1991-2020, 0.05°, public domain ("CHIRPS data is in
the public domain as registered with Creative Commons", NOAA ERDDAP licence attribute), blends
satellite and station data (incl. IDEAM). Derived: annual rainfall (mm/yr) and dry months (mean
monthly rainfall < ``DRY_MONTH_MM``). ERA5-Land rainfall was inflated on steep slopes (gap G-10).

Temperature and actual evaporation: ERA5-Land monthly averaged reanalysis 1991-2020, 0.1°,
CC BY 4.0, via the Copernicus Climate Data Store API (``cdsapi``; token injected by the session
proxy). ERA5-Land potential evaporation is downloaded but not used: implausibly high in the pilot
(D-42). The water term for F5 is rainfall − actual evaporation.

ERA5-Land monthly means of accumulated variables are in "m of water equivalent per day" (ERA5-Land
data documentation, ECMWF). ECMWF fluxes are positive downwards, so evaporation is stored negative;
the sign is checked on the downloaded data before conversion.
"""

import calendar
import zipfile
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
from mrv_lab.erw_siting.soil import with_retries  # noqa: E402

YEARS = tuple(range(1991, 2021))
PAD_DEG = 0.2

#: Dry month = mean rainfall below 60 mm: the Köppen-Geiger tropical threshold as used by
#: Peel, Finlayson & McMahon (2007), Hydrol. Earth Syst. Sci. 11, 1633-1644 (Af: Pdry >= 60 mm).
DRY_MONTH_MM = 60.0

# --- CHIRPS v2.0 -------------------------------------------------------------------------------

#: Monthly COGs, mm/month, nodata -9999 (checked 2026-11-14). Read with the GTiff driver
#: (GDAL does not recognise the ``.cog`` extension by itself).
CHIRPS_URL = (
    "https://data.chc.ucsb.edu/products/CHIRPS/v2.0/global_monthly/cogs/"
    "chirps-v2.0.{year}.{month:02d}.cog"
)
CHIRPS_NODATA = -9999.0
GDAL_HTTP_ENV = {"GDAL_HTTP_MAX_RETRY": 5, "GDAL_HTTP_RETRY_DELAY": 5, "GDAL_HTTP_TIMEOUT": 120}

# --- ERA5-Land ------------------------------------------------------------------------------

CDS_URL = "https://cds.climate.copernicus.eu/api"
ERA5_DATASET = "reanalysis-era5-land-monthly-means"

#: CDS request variable -> short name in the returned netCDF.
ERA5_VARIABLES: dict[str, str] = {
    "2m_temperature": "t2m",
    "potential_evaporation": "pev",
    "total_evaporation": "e",
    "total_precipitation": "tp",
}

#: Output grids: name -> (unit, resolution in metres used for the reprojected grid).
OUTPUTS: dict[str, tuple[str, float]] = {
    "rain_annual_mm": ("mm/yr", 5_000.0),
    "dry_months": ("months/yr", 5_000.0),
    "t2m_mean_c": ("°C", 10_000.0),
    "et_annual_mm": ("mm/yr", 10_000.0),
}


def pilot_bounds_4326(pilot: gpd.GeoDataFrame) -> tuple[float, float, float, float]:
    """(west, south, east, north) in degrees around all pilot departments, padded."""
    west, south, east, north = transform_bounds(pilot.crs, "EPSG:4326", *pilot.total_bounds)
    return west - PAD_DEG, south - PAD_DEG, east + PAD_DEG, north + PAD_DEG


def fetch_chirps(pilot: gpd.GeoDataFrame, raw_dir: Path | None = None) -> list[Path]:
    """Read the pilot window of every monthly map 1991-2020 (360 files), SHA-256 pinned."""
    raw_dir = raw_dir or io.raw_dir() / "chirps"
    raw_dir.mkdir(parents=True, exist_ok=True)
    bounds = pilot_bounds_4326(pilot)
    paths = []
    with rasterio.Env(**GDAL_HTTP_ENV):
        for year in YEARS:
            for month in range(1, 13):
                url = CHIRPS_URL.format(year=year, month=month)
                dest = raw_dir / f"chirps_{year}_{month:02d}.tif"
                if not dest.exists():
                    with_retries(lambda u=url, d=dest: _write_chirps_window(u, bounds, d))
                io.register_checksum(dest, f"{url} (window {tuple(round(b, 2) for b in bounds)})")
                paths.append(dest)
    return paths


def _write_chirps_window(url: str, bounds: tuple[float, ...], dest: Path) -> None:
    with rasterio.open(f"/vsicurl/{url}", driver="GTiff") as src:
        window = from_bounds(*bounds, transform=src.transform).round_offsets().round_lengths()
        data = src.read(1, window=window)
        profile = {
            "driver": "GTiff",
            "dtype": data.dtype,
            "count": 1,
            "height": data.shape[0],
            "width": data.shape[1],
            "crs": src.crs,
            "transform": src.window_transform(window),
            "nodata": CHIRPS_NODATA,
            "compress": "deflate",
        }
    part = dest.with_name(dest.name + ".part")
    with rasterio.open(part, "w", **profile) as out:
        out.write(data, 1)
    part.replace(dest)


def chirps_climatology(stack_mm: np.ndarray) -> np.ndarray:
    """Mean rainfall per calendar month (mm/month), shape (12, rows, cols), from monthly maps."""
    stack = stack_mm.astype("float64")
    stack[stack == CHIRPS_NODATA] = np.nan
    return stack.reshape(len(YEARS), 12, *stack.shape[1:]).mean(axis=0)


def rainfall_indicators(monthly_mm: np.ndarray, dry_month_mm: float = DRY_MONTH_MM) -> dict:
    """Annual rainfall (mm/yr) and count of dry months from a (12, rows, cols) climatology."""
    stack = monthly_mm.astype("float64")
    return {
        "rain_annual_mm": stack.sum(axis=0),
        "dry_months": (stack < dry_month_mm).sum(axis=0).astype("float64"),
    }


def era5_request(bounds: tuple[float, float, float, float]) -> dict:
    """CDS request for monthly means 1991-2020; ``area`` is [north, west, south, east]."""
    west, south, east, north = bounds
    return {
        "product_type": ["monthly_averaged_reanalysis"],
        "variable": list(ERA5_VARIABLES),
        "year": [str(y) for y in YEARS],
        "month": [f"{m:02d}" for m in range(1, 13)],
        "time": ["00:00"],
        "data_format": "netcdf",
        "download_format": "unarchived",
        "area": [round(north, 2), round(west, 2), round(south, 2), round(east, 2)],
    }


def fetch_era5land(pilot: gpd.GeoDataFrame, raw_dir: Path | None = None) -> dict[str, Path]:
    """Download ERA5-Land once and store one GeoTIFF per variable (360 monthly bands), pinned.

    The netCDF from the CDS is not byte-reproducible (it carries request metadata), so the
    pinned files are the per-variable GeoTIFFs extracted from it.
    """
    raw_dir = raw_dir or io.raw_dir() / "era5land"
    raw_dir.mkdir(parents=True, exist_ok=True)
    tifs = {short: raw_dir / f"{short}_1991-2020_monthly.tif" for short in ERA5_VARIABLES.values()}
    if not all(p.exists() for p in tifs.values()):
        import cdsapi  # imported here: only needed for the first download

        download = raw_dir / "era5land_1991-2020.download"
        if not download.exists():
            client = cdsapi.Client(url=CDS_URL, key="proxy-injected", quiet=True)
            client.retrieve(ERA5_DATASET, era5_request(pilot_bounds_4326(pilot)), str(download))
        for short, tif in tifs.items():
            _extract_variable(download, short, tif, raw_dir)
    request = era5_request(pilot_bounds_4326(pilot))
    for short, tif in tifs.items():
        io.register_checksum(tif, f"CDS {ERA5_DATASET} {short} area={request['area']} 1991-2020")
    return tifs


def _netcdf_files(download: Path, raw_dir: Path) -> list[Path]:
    """The netCDF file(s) in the download, unzipping if the CDS returned an archive."""
    if zipfile.is_zipfile(download):
        with zipfile.ZipFile(download) as archive:
            archive.extractall(raw_dir / "era5land_unzipped")
        return sorted((raw_dir / "era5land_unzipped").glob("*.nc"))
    return [download]


def _extract_variable(download: Path, short: str, dest: Path, raw_dir: Path) -> None:
    for nc in _netcdf_files(download, raw_dir):
        try:
            src = rasterio.open(f"netcdf:{nc}:{short}")
        except rasterio.errors.RasterioIOError:
            continue
        with src:
            data = src.read()
            profile = {
                "driver": "GTiff",
                "dtype": "float32",
                "count": data.shape[0],
                "height": data.shape[1],
                "width": data.shape[2],
                "crs": src.crs or "EPSG:4326",
                "transform": src.transform,
                "nodata": np.nan,
                "compress": "deflate",
            }
            data = np.where(data == src.nodata, np.nan, data) if src.nodata is not None else data
        with rasterio.open(dest, "w", **profile) as out:
            out.write(data.astype("float32"))
        return
    raise FileNotFoundError(f"Variable {short!r} not found in {download}")


def days_in_months(years: tuple[int, ...] = YEARS) -> np.ndarray:
    """Days per month for every (year, month) in request order: shape (len(years) * 12,)."""
    return np.array([calendar.monthrange(y, m)[1] for y in years for m in range(1, 13)])


def monthly_climatology_mm(tp_m_day: np.ndarray) -> np.ndarray:
    """Mean rainfall per calendar month (mm/month), shape (12, rows, cols), from monthly means."""
    days = days_in_months(YEARS)[:, None, None]
    monthly_mm = tp_m_day * 1000.0 * days
    return monthly_mm.reshape(len(YEARS), 12, *tp_m_day.shape[1:]).mean(axis=0)


def era5_indicators(t2m_k: np.ndarray, pev_m_day: np.ndarray, e_m_day: np.ndarray) -> dict:
    """Mean temperature (°C) and annual potential / actual evaporation (mm/yr, positive = loss)."""
    days = days_in_months(YEARS)[:, None, None]
    n_years = len(YEARS)
    return {
        "t2m_mean_c": np.nanmean(t2m_k, axis=0) - 273.15,
        "pet_annual_mm": -np.nansum(pev_m_day * 1000.0 * days, axis=0) / n_years,
        "et_annual_mm": -np.nansum(e_m_day * 1000.0 * days, axis=0) / n_years,
    }


def to_work_grid(
    data: np.ndarray,
    src_transform: rasterio.Affine,
    src_crs,  # noqa: ANN001
    outline: gpd.GeoSeries,
    resolution_m: float,
) -> tuple[np.ndarray, rasterio.Affine]:
    """Reproject to WORK_CRS (bilinear) and set NaN outside ``outline``."""
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
        resolution=resolution_m,
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
    out[
        geometry_mask(
            outline.to_crs(WORK_CRS).geometry, out_shape=out.shape, transform=dst_transform
        )
    ] = np.nan
    return out, dst_transform


def process_climate(
    era5: dict[str, Path],
    chirps: list[Path],
    pilot: gpd.GeoDataFrame,
    out_dir: Path | None = None,
) -> dict[tuple[str, str], Path]:
    """Compute the indicators and write one GeoTIFF per (department, indicator)."""
    out_dir = out_dir or io.interim_dir() / "erw_siting" / "climate"
    with rasterio.open(chirps[0]) as src:
        rain_tf, rain_crs = src.transform, src.crs
    stack = np.stack([rasterio.open(p).read(1) for p in chirps])
    grids = {
        name: (grid, rain_tf, rain_crs)
        for name, grid in rainfall_indicators(chirps_climatology(stack)).items()
    }
    stacks = {}
    for short, path in era5.items():
        with rasterio.open(path) as src:
            stacks[short] = src.read().astype("float64")
            era_tf, era_crs = src.transform, src.crs
    if np.nanmean(stacks["e"]) > 0:
        raise ValueError("ERA5-Land evaporation is positive on average: sign convention changed?")
    era = era5_indicators(stacks["t2m"], stacks["pev"], stacks["e"])
    for name in ("t2m_mean_c", "et_annual_mm"):
        grids[name] = (era[name], era_tf, era_crs)

    outputs: dict[tuple[str, str], Path] = {}
    for _, dept in pilot.iterrows():
        outline = gpd.GeoSeries([dept.geometry], crs=pilot.crs)
        for name, (grid, transform, crs) in grids.items():
            projected, dst_tf = to_work_grid(grid, transform, crs, outline, OUTPUTS[name][1])
            dest = out_dir / dept["name"].replace(" ", "_") / f"{name}.tif"
            dest.parent.mkdir(parents=True, exist_ok=True)
            profile = {
                "driver": "GTiff",
                "dtype": "float32",
                "count": 1,
                "height": projected.shape[0],
                "width": projected.shape[1],
                "crs": WORK_CRS,
                "transform": dst_tf,
                "nodata": np.nan,
                "compress": "deflate",
            }
            with rasterio.open(dest, "w", **profile) as out:
                out.write(projected, 1)
            outputs[(dept["name"], name)] = dest
    return outputs


def save_climate_qc(
    processed: dict[tuple[str, str], Path], pilot: gpd.GeoDataFrame, out_dir: Path | None = None
) -> tuple[list[Path], Path]:
    """One QC map per indicator (three departments) and a min / median / max table."""
    out_dir = out_dir or io.interim_dir() / "erw_siting" / "qc"
    out_dir.mkdir(parents=True, exist_ok=True)
    names = list(pilot["name"])
    rows, pngs = [], []
    for indicator, (unit, _) in OUTPUTS.items():
        grids = []
        for name in names:
            with rasterio.open(processed[(name, indicator)]) as src:
                grid, b = src.read(1), src.bounds
            inside = grid[~np.isnan(grid)]
            rows.append(
                {
                    "department": name,
                    "indicator": indicator,
                    "unit": unit,
                    "min": float(inside.min()),
                    "median": float(np.median(inside)),
                    "max": float(inside.max()),
                }
            )
            grids.append((grid, b))
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
                interpolation="nearest",
            )
            ax.set_title(name, fontsize=9)
            ax.set_axis_off()
        fig.colorbar(image, ax=axes, shrink=0.7, label=f"{indicator} ({unit})")
        fig.suptitle(f"QC — climate 1991-2020: {indicator} ({WORK_CRS})", fontsize=10)
        png = out_dir / f"climate_{indicator}.png"
        fig.savefig(png, dpi=110, bbox_inches="tight")
        plt.close(fig)
        pngs.append(png)
    csv = out_dir / "climate_summary.csv"
    pd.DataFrame(rows).round(2).to_csv(csv, index=False)
    return pngs, csv
