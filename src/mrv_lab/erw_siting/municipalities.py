"""Municipal tables of analysis 01 (F8, decision D-68).

DANE's own MGN download is not reachable from the cloud session (D-11) and David could not
download it either, so municipal boundaries come from OCHA's Common Operational Dataset on HDX
(``cod-ab-col``), whose stated source is DANE: layer ``col_admbnda_adm2_mgn_20200416`` (1,122
municipalities and non-municipalised areas, MGN dated 2020-04-16), licence CC BY-IGO 3.0.

Each 1 km cell is assigned to the municipality containing its centre. Table per municipality
(base run, medium grain): candidate area, area with P(net > 0) > 0.8, median road distance to rock,
share of acid topsoil, median P(net > 0).
"""

from pathlib import Path

import geopandas as gpd
import pandas as pd

from mrv_lab import io
from mrv_lab.erw_siting import database as db
from mrv_lab.erw_siting.regions import WORK_CRS

HDX_URL = (
    "https://data.humdata.org/dataset/50ea7fee-f9af-45a7-8a52-abb9c790a0b6/resource/"
    "da4a3090-43d7-4f0b-8b51-2de9718f69c4/download/col-administrative-divisions-geodatabase.zip"
)
LAYER = "col_admbnda_adm2_mgn_20200416"
GDB = "COL_AdminBoundaries_candidate.gdb"
HIGH_PROBABILITY = 0.8  # plan §6 deliverable 4


def fetch() -> Path:
    """Download the HDX geodatabase once (SHA-256 pinned)."""
    return io.download_file(
        HDX_URL, io.raw_dir() / "hdx_cod_ab" / "col_admin_gdb.zip", timeout_s=600
    )


def read_municipalities(zip_path: Path, departments: list[str]) -> gpd.GeoDataFrame:
    """Municipal polygons of ``departments`` (names as in ``cells.department``), EPSG:9377."""
    gdf = gpd.read_file(f"/vsizip/{zip_path}/{GDB}", layer=LAYER)
    gdf = gdf[gdf["admin1Name_es"].isin(departments)]
    missing = set(departments) - set(gdf["admin1Name_es"])
    if missing:
        raise ValueError(f"Departments not found in the HDX layer: {sorted(missing)}")
    return gdf[["admin2Pcode", "admin2Name_es", "admin1Name_es", "geometry"]].to_crs(WORK_CRS)


def assign_cells(cells: pd.DataFrame, municipalities: gpd.GeoDataFrame) -> pd.Series:
    """Municipality code (``admin2Pcode``) of each cell centre; NaN if outside every polygon."""
    points = gpd.GeoDataFrame(
        cells[["cell_id"]],
        geometry=gpd.points_from_xy(cells["x_center_m"], cells["y_center_m"]),
        crs=WORK_CRS,
    )
    joined = gpd.sjoin(points, municipalities, how="left", predicate="within")
    joined = joined[~joined.index.duplicated()]
    return joined.set_index("cell_id")["admin2Pcode"]


def municipal_table(results: pd.DataFrame, codes: pd.Series, names: pd.DataFrame) -> pd.DataFrame:
    """Aggregate base-run candidate cells per municipality (areas from the cells' km2)."""
    cand = results[(results["candidate"] == 1)].copy()
    cand["admin2Pcode"] = cand["cell_id"].map(codes)
    cand = cand.dropna(subset=["admin2Pcode"])
    cand["high_km2"] = cand["area_in_department_km2"].where(
        cand["p_net_positive"] > HIGH_PROBABILITY, 0.0
    )
    table = cand.groupby("admin2Pcode").agg(
        candidate_area_km2=("area_in_department_km2", "sum"),
        area_p_net_positive_gt_0_8_km2=("high_km2", "sum"),
        median_p_net_positive=("p_net_positive", "median"),
        median_road_km_to_rock=("road_km", "median"),
        share_acid_topsoil=("lime_demand", lambda s: float(pd.to_numeric(s).mean())),
    )
    out = names.set_index("admin2Pcode").join(table, how="inner").reset_index()
    out = out.rename(
        columns={
            "admin2Pcode": "municipality_code",
            "admin2Name_es": "municipality",
            "admin1Name_es": "department",
        }
    )
    return out.sort_values(
        ["department", "area_p_net_positive_gt_0_8_km2"], ascending=[True, False]
    ).round(3)


def run(results: pd.DataFrame, out_csv: Path, path: Path | None = None) -> pd.DataFrame:
    """Build and write the municipal table for the base run; returns it."""
    path = path or db.database_path()
    with db.connect(path) as con:
        cells = pd.read_sql("SELECT cell_id, x_center_m, y_center_m FROM cells", con)
    departments = sorted(results["department"].dropna().unique())
    munis = read_municipalities(fetch(), departments)
    codes = assign_cells(cells, munis)
    base = results[results["scenario_id"] == db.BASE_SCENARIO]
    table = municipal_table(base, codes, munis.drop(columns="geometry"))
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(out_csv, index=False)
    return table
