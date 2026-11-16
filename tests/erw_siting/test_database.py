"""Tests for erw_siting.database (empty GeoPackage schema, no network)."""

import sqlite3
from pathlib import Path

import geopandas as gpd
import pandas as pd
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


def _registry() -> pd.DataFrame:
    source = {"citation": "A 2020", "doi_or_url": "doi:10/x", "locator": "Table 1"}
    return pd.DataFrame(
        [
            {
                "group": "rock",
                "id": "a",
                "name": "A",
                "value": 2.0,
                "unit": "wt%",
                "range": [1.0, 3.0],
                "distribution": {"type": "triangular"},
                "source": source,
                "quality": "literature",
                "status": "ok",
                "notes": "",
            },
            {
                "group": "lca",
                "id": "b",
                "name": "B",
                "value": None,
                "unit": "kWh/t",
                "range": None,
                "distribution": None,
                "source": None,
                "quality": None,
                "status": "missing",
                "notes": "",
            },
        ]
    )


def test_parameters_and_base_scenario(tmp_path: Path) -> None:
    path = db.create_database(tmp_path / "erw.gpkg")
    db.write_parameters(_registry(), path)
    base = db.scenario_values(db.BASE_SCENARIO, path).set_index("parameter_id")
    assert base.loc["a", "value"] == 2.0 and pd.isna(base.loc["a", "override_value"])
    assert pd.isna(base.loc["b", "value"])  # missing stays empty, never defaulted
    with db.connect(path) as con:
        row = con.execute(
            "SELECT range_min, range_max, citation FROM parameters WHERE parameter_id = 'a'"
        ).fetchone()
        citable = con.execute("SELECT citable FROM scenarios").fetchone()[0]
    assert row == (1.0, 3.0, "A 2020") and citable == 1


def test_scenario_overrides_only_what_changes(tmp_path: Path) -> None:
    path = db.create_database(tmp_path / "erw.gpkg")
    db.write_parameters(_registry(), path)
    db.add_scenario("s1", "Higher a", overrides={"a": 2.5}, rock_type="ultramafic", path=path)
    values = db.scenario_values("s1", path).set_index("parameter_id")
    assert values.loc["a", "value"] == 2.5 and values.loc["a", "base_value"] == 2.0
    with db.connect(path) as con:
        assert (
            con.execute("SELECT citable FROM scenarios WHERE scenario_id='s1'").fetchone()[0] == 0
        )
    with pytest.raises(KeyError):
        db.add_scenario("s2", "bad", overrides={"zzz": 1.0}, path=path)
    with pytest.raises(KeyError):
        db.scenario_values("nope", path)
