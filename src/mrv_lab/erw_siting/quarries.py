"""Potential rock sources: suitable rock with truck access by road (plan F3).

No licensed quarry polygons exist (ANM titles dropped, D-09), so rock sources are **potential**
points: places on truck-usable roads that pass through or near suitable rock (F2 classes).

Decisions (D-46, David 2026-11-14), all parameters tested in F7:
- road classes usable by trucks: motorway, trunk, primary, secondary, tertiary, unclassified (and
  their links); no residential streets, service roads, tracks or paths;
- roads within ``MAX_ACCESS_KM`` = 5 km of suitable rock; each point records its exact access
  distance (``access_km``, 0 = road on the rock);
- density: at most one point per ``SPACING_KM`` x ``SPACING_KM`` (5 x 5 km) grid square, the road
  point closest to the rock (roads are sampled every ``DENSE_STEP_KM`` first; OSM splits roads into
  many short segments, so per-segment sampling over-counts);
- Apta and Mixta both produce points; Mixta points are flagged and excluded by default (D-40).

Roads: OpenStreetMap via the HOT export on HDX, ODbL 1.0 (data/SOURCES.md row D12). Rock: SGC
(internal use only, D-08), so the outputs stay in gitignored folders.
"""

from pathlib import Path

import geopandas as gpd
import matplotlib
import numpy as np
import pandas as pd
import pyogrio
from shapely.geometry import LineString, MultiLineString, Point
from shapely.ops import linemerge, unary_union

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from mrv_lab import io, plotting  # noqa: E402
from mrv_lab.erw_siting.regions import WORK_CRS  # noqa: E402

#: HOT OpenStreetMap export for Colombia on HDX (dataset hotosm_col_roads), checked 2026-11-14.
ROADS_URL = (
    "https://production-raw-data-api.s3.amazonaws.com/ISO3/COL/roads/hotosm_col_roads_osm_gpkg.zip"
)

TRUCK_ROAD_CLASSES: tuple[str, ...] = (
    "motorway",
    "motorway_link",
    "trunk",
    "trunk_link",
    "primary",
    "primary_link",
    "secondary",
    "secondary_link",
    "tertiary",
    "tertiary_link",
    "unclassified",
)
MAX_ACCESS_KM = 5.0
SPACING_KM = 5.0
DENSE_STEP_KM = 0.5
SOURCE_CLASSES = ("Apta", "Mixta")


def fetch_roads() -> Path:
    """Download the national OSM roads export once (SHA-256 pinned)."""
    return io.download_file(
        ROADS_URL, io.raw_dir() / "osm" / "hotosm_col_roads_osm_gpkg.zip", timeout_s=900
    )


def read_truck_roads(path: Path) -> gpd.GeoDataFrame:
    """Truck-usable road lines (``TRUCK_ROAD_CLASSES``), reprojected to WORK_CRS."""
    classes = ", ".join(f"'{c}'" for c in TRUCK_ROAD_CLASSES)
    roads = pyogrio.read_dataframe(
        f"zip://{path}!roads.gpkg",
        columns=["highway", "adm1_name", "adm2_name"],
        where=f"highway IN ({classes})",
    )
    roads = roads[roads.geometry.geom_type.isin(["LineString", "MultiLineString"])]
    return roads.to_crs(WORK_CRS)


def sample_points(line: LineString | MultiLineString, spacing_m: float) -> list[Point]:
    """Points every ``spacing_m`` along each part, starting at the middle of the first interval."""
    parts = line.geoms if isinstance(line, MultiLineString) else [line]
    points = []
    for part in parts:
        n = max(1, int(part.length // spacing_m))
        step = part.length / n
        points.extend(part.interpolate(step * (i + 0.5)) for i in range(n))
    return points


def potential_sources(
    roads: gpd.GeoDataFrame,
    rock: gpd.GeoDataFrame,
    max_access_km: float = MAX_ACCESS_KM,
    spacing_km: float = SPACING_KM,
) -> gpd.GeoDataFrame:
    """Potential rock-source points from roads near rock polygons of each source class.

    ``rock`` needs columns ``unit_code``, ``final_class``, ``ultramafic`` and polygons in WORK_CRS.
    Apta is processed first; a road stretch already near Apta rock is not reused for Mixta.
    """
    rows = []
    used = None
    for cls in SOURCE_CLASSES:
        units = rock[rock["final_class"] == cls]
        if units.empty:
            continue
        zone = unary_union(units.geometry.buffer(max_access_km * 1000))
        near = roads[roads.intersects(zone)]
        if near.empty:
            continue
        lines = unary_union(near.geometry.intersection(zone).tolist())
        if used is not None:
            lines = lines.difference(used)
        used = zone if used is None else used.union(zone)
        if lines.is_empty:
            continue
        merged = linemerge(lines) if lines.geom_type == "MultiLineString" else lines
        points = sample_points(merged, DENSE_STEP_KM * 1000)
        pts = gpd.GeoDataFrame(geometry=points, crs=WORK_CRS)
        joined = gpd.sjoin_nearest(
            pts, units[["unit_code", "ultramafic", "geometry"]], distance_col="access_m"
        )
        joined = joined[~joined.index.duplicated()]
        road_class = gpd.sjoin_nearest(pts, near[["highway", "geometry"]])["highway"]
        joined["road_class"] = road_class[~road_class.index.duplicated()]
        joined["final_class"] = cls
        rows.append(joined.drop(columns="index_right"))
    if not rows:
        return gpd.GeoDataFrame(
            columns=[
                "rock_source_id",
                "unit_code",
                "origin",
                "final_class",
                "road_class",
                "access_km",
                "ultramafic",
                "geometry",
            ],
            geometry="geometry",
            crs=WORK_CRS,
        )
    out = gpd.GeoDataFrame(pd.concat(rows, ignore_index=True), crs=WORK_CRS)
    out = out[out["access_m"] <= max_access_km * 1000]
    out = thin_to_grid(out, spacing_km)
    out["access_km"] = (out.pop("access_m") / 1000).round(3)
    out["origin"] = "potential"
    out["ultramafic"] = out["ultramafic"].astype(bool).astype(int)
    out["rock_source_id"] = [f"RS{i:05d}" for i in range(1, len(out) + 1)]
    cols = [
        "rock_source_id",
        "unit_code",
        "origin",
        "final_class",
        "road_class",
        "access_km",
        "ultramafic",
        "geometry",
    ]
    return out[cols]


def thin_to_grid(points: gpd.GeoDataFrame, spacing_km: float) -> gpd.GeoDataFrame:
    """Keep, per class and ``spacing_km`` grid square, the point with the smallest ``access_m``."""
    size = spacing_km * 1000
    keyed = points.assign(
        gx=np.floor(points.geometry.x / size).astype(int),
        gy=np.floor(points.geometry.y / size).astype(int),
    ).sort_values("access_m", kind="stable")
    kept = keyed.drop_duplicates(subset=["final_class", "gx", "gy"], keep="first")
    return kept.drop(columns=["gx", "gy"]).sort_index().reset_index(drop=True)


def save_quarries(
    sources: gpd.GeoDataFrame,
    rock: gpd.GeoDataFrame,
    departments: gpd.GeoDataFrame,
    pilot: gpd.GeoDataFrame,
    out_dir: Path | None = None,
) -> tuple[Path, Path, Path]:
    """GeoPackage of sources, QC map and QC table (gitignored: SGC-derived, D-08)."""
    out_dir = out_dir or io.interim_dir() / "erw_siting" / "geology"
    qc = io.interim_dir() / "erw_siting" / "qc"
    out_dir.mkdir(parents=True, exist_ok=True)
    qc.mkdir(parents=True, exist_ok=True)
    gpkg = out_dir / "rock_sources_potential.gpkg"
    png = qc / "rock_sources_potential.png"
    csv = qc / "rock_sources_summary.csv"
    sources.to_file(gpkg, layer="rock_sources", driver="GPKG")
    summary = sources.groupby(["final_class", "road_class"]).agg(
        n_points=("rock_source_id", "size"), access_km_median=("access_km", "median")
    )
    summary.round(2).to_csv(csv)

    fig, ax = plt.subplots(figsize=(6, 7))
    departments.plot(ax=ax, color="#EEEEEE", edgecolor="white", linewidth=0.4)
    rock[rock["final_class"] == "Apta"].plot(ax=ax, color=plotting.GREY, edgecolor="none")
    for cls, color, size in (
        ("Mixta", plotting.OKABE_ITO["orange"], 2),
        ("Apta", plotting.HIGHLIGHT, 3),
    ):
        part = sources[sources["final_class"] == cls]
        if not part.empty:
            part.plot(ax=ax, color=color, markersize=size)
    pilot.boundary.plot(ax=ax, color="black", linewidth=0.8)
    handles = [
        plt.Rectangle((0, 0), 1, 1, color=plotting.GREY),
        plt.Line2D([], [], marker="o", ls="", color=plotting.HIGHLIGHT),
        plt.Line2D([], [], marker="o", ls="", color=plotting.OKABE_ITO["orange"]),
        plt.Line2D([], [], color="black"),
    ]
    ax.legend(
        handles,
        ["Apta rock", "Potential source (Apta)", "Potential source (Mixta)", "Pilot departments"],
        loc="lower left",
        fontsize=8,
    )
    ax.set_title(f"QC — potential rock sources ({WORK_CRS}) — internal use", fontsize=9)
    ax.set_axis_off()
    fig.savefig(png, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return gpkg, png, csv


def access_km_summary(sources: gpd.GeoDataFrame) -> pd.Series:
    """Quantiles of access distance (km) — for the sensitivity on ``MAX_ACCESS_KM``."""
    return sources["access_km"].quantile([0.5, 0.9, 1.0]) if len(sources) else pd.Series(np.nan)
