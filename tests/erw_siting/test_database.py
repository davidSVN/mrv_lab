"""Tests for erw_siting.database (empty GeoPackage schema, no network)."""

import sqlite3
from pathlib import Path

import geopandas as gpd
import pytest

from mrv_lab.erw_siting import database as db


def test_creates_every_table_registered(tmp_path: Path) -> None:
    path = db.create_database(tmp_path / "erw.gpkg")
    assert sorted(db.list_tables(path)) == sorted(db.TABLES)


def test_spatial_tables_use_work_crs(tmp_path: Path) -> None:
    path = db.create_database(tmp_path / "erw.gpkg")
    cells = gpd.read_file(path, layer="cells")
    assert cells.crs.to_epsg() == 9377
    assert {"cell_id", "department", "area_in_department_km2"} <= set(cells.columns)


def test_refuses_to_overwrite_without_flag(tmp_path: Path) -> None:
    path = db.create_database(tmp_path / "erw.gpkg")
    with pytest.raises(FileExistsError):
        db.create_database(path)
    assert db.create_database(path, overwrite=True) == path


def test_foreign_keys_and_unique_cells_enforced(tmp_path: Path) -> None:
    path = db.create_database(tmp_path / "erw.gpkg")
    with db.connect(path) as con:
        with pytest.raises(sqlite3.IntegrityError):  # run_id and cell_id do not exist
            con.execute(
                "INSERT INTO cell_results (run_id, cell_id, candidate) VALUES ('r', 'c', 1)"
            )
        unique = con.execute(
            "SELECT sql FROM sqlite_master WHERE name = 'ux_cells_cell_id'"
        ).fetchone()[0]
    assert "UNIQUE" in unique.upper()


def test_result_columns_cover_blocks_1_and_2(tmp_path: Path) -> None:
    path = db.create_database(tmp_path / "erw.gpkg")
    with sqlite3.connect(path) as con:
        cols = {r[1] for r in con.execute("PRAGMA table_info(cell_results)")}
    expected = {
        "candidate",
        "excluded_by",
        "cdr_max_tco2_per_t",
        "f_diss",
        "f_loss",
        "cdr_gross_tco2_per_t",
        "e_grind_tco2_per_t",
        "e_transport_tco2_per_t",
        "e_spread_tco2_per_t",
        "rock_source_id",
        "road_km",
        "breakeven_km",
        "margin_km",
        "net_ha_p5_tco2_per_ha_yr",
        "net_ha_p50_tco2_per_ha_yr",
        "net_ha_p95_tco2_per_ha_yr",
        "p_net_positive",
        "lime_demand",
        "ultramafic_source",
        "data_quality",
    }
    assert expected <= cols
