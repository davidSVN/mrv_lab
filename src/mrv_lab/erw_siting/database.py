"""Data model of the ERW siting analysis: one GeoPackage with cell tables (plan F5a).

Architecture (decisions D-25, D-44): a GeoPackage (SQLite with spatial support: real SQL tables,
keys and spatial indexes, no server) now; the same schema migrates to PostgreSQL + PostGIS with one
``ogr2ogr`` load in phase F9 (triggers: dashboard / web app, several writers, national scale).
Portability rules: SRID 9377 everywhere, explicit primary and foreign keys, plain SQL types
(TEXT, INTEGER, REAL), units in column names.

The database lives in ``data/interim/`` (gitignored: it holds SGC-derived data, D-08); this schema
is code and is versioned. Tables are created empty here and filled in F3, F5, F6 and F7.

Cells are 1 km x 1 km squares on EPSG:9377 (D-44); a border cell belongs to the department holding
most of its area. Soil and climate go to the long table ``cell_values`` (one row per cell, variable
and statistic), so new variables or rock types do not change the schema.
"""

import sqlite3
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, box

from mrv_lab import io
from mrv_lab.erw_siting.regions import WORK_CRS

CELL_SIZE_M = 1_000

#: Spatial tables: name -> (geometry type, {column: pandas dtype}). Created through OGR so the
#: GeoPackage metadata (SRS 9377, geometry columns, spatial index) is written correctly.
SPATIAL_TABLES: dict[str, tuple[str, dict[str, str]]] = {
    "cells": (
        "Polygon",
        {
            "cell_id": "str",  # "E{x_km}_N{y_km}" of the lower-left corner, EPSG:9377 km
            "department": "str",
            "x_center_m": "float64",
            "y_center_m": "float64",
            "area_in_department_km2": "float64",
        },
    ),
    "rock_sources": (
        "Point",
        {
            "rock_source_id": "str",
            "unit_code": "int64",
            "origin": "str",  # "potential" in v0.1 (D-09: no licensed quarry polygons)
        },
    ),
}

#: Unique keys on the spatial tables (OGR adds its own integer ``fid`` primary key).
SPATIAL_KEYS = {"cells": "cell_id", "rock_sources": "rock_source_id"}

#: Attribute tables as portable SQL (SQLite and PostgreSQL accept these types and constraints).
ATTRIBUTE_TABLES: dict[str, str] = {
    "sources": """
        CREATE TABLE sources (
            source_id TEXT PRIMARY KEY,          -- e.g. 'D8' (data/SOURCES.md)
            name TEXT NOT NULL,
            url TEXT,
            license TEXT,
            redistribution TEXT,                 -- yes / no / unclear
            accessed TEXT                        -- YYYY-MM-DD
        )""",
    "cell_filters": """
        CREATE TABLE cell_filters (
            cell_id TEXT PRIMARY KEY REFERENCES cells (cell_id),
            protected_frac REAL,                 -- share of the cell inside RUNAP (0-1)
            frontier_unconditioned_frac REAL,    -- UPRA "No condicionada" (0-1)
            frontier_conditioned_frac REAL,      -- UPRA "Condicionada" (0-1)
            agro_use_frac REAL,                  -- MapBiomas 2024 classes 21/35/74 (0-1)
            slope_median_pct REAL,
            slope_gt8_frac REAL,
            slope_gt12_frac REAL,
            slope_smoothing_px INTEGER           -- NULL = raw slope (D-36)
        )""",
    "cell_values": """
        CREATE TABLE cell_values (
            cell_id TEXT NOT NULL REFERENCES cells (cell_id),
            layer TEXT NOT NULL,                 -- 'soil' | 'climate' | ...
            variable TEXT NOT NULL,              -- e.g. 'phh2o', 'rain_annual_mm'
            statistic TEXT NOT NULL,             -- e.g. 'mean', 'Q0.05', 'Q0.95'
            value REAL,
            unit TEXT NOT NULL,
            source_id TEXT REFERENCES sources (source_id),
            PRIMARY KEY (cell_id, variable, statistic)
        )""",
    "rock_units": """
        CREATE TABLE rock_units (
            unit_code INTEGER PRIMARY KEY,       -- SGC CodigoUC
            symbol TEXT,
            final_class TEXT NOT NULL,           -- Apta | Mixta | No apta (D-40, D-43)
            rock_types TEXT,                     -- '; '-separated (D-39)
            ultramafic INTEGER NOT NULL          -- 0/1
        )""",
    "cell_routes": """
        CREATE TABLE cell_routes (
            cell_id TEXT NOT NULL REFERENCES cells (cell_id),
            rock_source_id TEXT NOT NULL REFERENCES rock_sources (rock_source_id),
            road_km REAL,
            straight_km REAL,
            PRIMARY KEY (cell_id, rock_source_id)
        )""",
    "runs": """
        CREATE TABLE runs (
            run_id TEXT PRIMARY KEY,
            created_utc TEXT NOT NULL,
            code_commit TEXT,
            parameters_json TEXT NOT NULL,       -- dose, horizon, grain size, scenario, filters
            seed INTEGER,
            notes TEXT
        )""",
    "cell_results": """
        CREATE TABLE cell_results (
            run_id TEXT NOT NULL REFERENCES runs (run_id),
            cell_id TEXT NOT NULL REFERENCES cells (cell_id),
            candidate INTEGER NOT NULL,          -- 0/1: passes the four hard filters
            excluded_by TEXT,                    -- protected | frontier | land_use | slope
            rock_source_id TEXT REFERENCES rock_sources (rock_source_id),
            road_km REAL,
            cdr_max_tco2_per_t REAL,             -- theoretical capture per t rock
            f_diss REAL,                         -- dissolved fraction over the horizon (0-1)
            f_loss REAL,                         -- soil losses (0-1)
            cdr_gross_tco2_per_t REAL,
            e_grind_tco2_per_t REAL,
            e_transport_tco2_per_t REAL,
            e_spread_tco2_per_t REAL,
            breakeven_km REAL,
            margin_km REAL,                      -- breakeven_km - road_km
            net_ha_p5_tco2_per_ha_yr REAL,
            net_ha_p50_tco2_per_ha_yr REAL,
            net_ha_p95_tco2_per_ha_yr REAL,
            p_net_positive REAL,                 -- probability that net removal > 0
            lime_demand INTEGER,                 -- 0/1: pH < 5.5 (agronomic axis)
            ultramafic_source INTEGER,           -- 0/1: assigned rock is ultramafic (Ni/Cr)
            data_quality TEXT,                   -- ';'-separated flags
            PRIMARY KEY (run_id, cell_id)
        )""",
}

TABLES = (*SPATIAL_TABLES, *ATTRIBUTE_TABLES)


def database_path() -> Path:
    """Default location: ``data/interim/erw_siting/erw_siting.gpkg`` (gitignored)."""
    return io.interim_dir() / "erw_siting" / "erw_siting.gpkg"


def _empty_layer(geometry_type: str, columns: dict[str, str]) -> gpd.GeoDataFrame:
    sample = box(0, 0, 1, 1) if geometry_type == "Polygon" else Point(0, 0)
    gdf = gpd.GeoDataFrame(
        {name: pd.Series(dtype=dtype) for name, dtype in columns.items()},
        geometry=gpd.GeoSeries([sample], crs=WORK_CRS).iloc[:0],
        crs=WORK_CRS,
    )
    return gdf


def create_database(path: Path | None = None, overwrite: bool = False) -> Path:
    """Create the empty GeoPackage with every table, key and index.

    Raises:
        FileExistsError: the file exists and ``overwrite`` is False (never silently replaced).
    """
    path = path or database_path()
    if path.exists():
        if not overwrite:
            raise FileExistsError(f"{path} exists; pass overwrite=True to rebuild it.")
        path.unlink()
    path.parent.mkdir(parents=True, exist_ok=True)

    for name, (geometry_type, columns) in SPATIAL_TABLES.items():
        _empty_layer(geometry_type, columns).to_file(
            path, layer=name, driver="GPKG", geometry_type=geometry_type
        )

    with sqlite3.connect(path) as con:
        for table, key in SPATIAL_KEYS.items():
            con.execute(f"CREATE UNIQUE INDEX ux_{table}_{key} ON {table} ({key})")
        for name, ddl in ATTRIBUTE_TABLES.items():
            con.execute(ddl)
            con.execute(
                "INSERT INTO gpkg_contents (table_name, data_type, identifier) "
                "VALUES (?, 'attributes', ?)",
                (name, name),
            )
        con.execute("CREATE INDEX ix_cell_values_variable ON cell_values (variable, statistic)")
        con.execute("CREATE INDEX ix_cell_results_cell ON cell_results (cell_id)")
    return path


def connect(path: Path | None = None) -> sqlite3.Connection:
    """SQLite connection with foreign keys enforced, for the attribute tables.

    Spatial tables (``cells``, ``rock_sources``) are written through geopandas / OGR: their
    GeoPackage spatial-index triggers need GDAL's SQL functions, which plain ``sqlite3`` lacks.
    """
    con = sqlite3.connect(path or database_path())
    con.execute("PRAGMA foreign_keys = ON")
    return con


def list_tables(path: Path | None = None) -> list[str]:
    """Tables registered in the GeoPackage (spatial and attribute)."""
    with sqlite3.connect(path or database_path()) as con:
        rows = con.execute("SELECT table_name FROM gpkg_contents ORDER BY table_name").fetchall()
    return [r[0] for r in rows]
