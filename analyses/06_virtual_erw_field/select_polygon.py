"""Select a ~5000 ha contiguous cropland polygon in the Altillanura, Meta, Colombia.

Criteria (plan §1.1):
- Cropland: ESA WorldCover 2021 v200, class 40 (cropland)
- Slope: < 3° (Copernicus DEM GLO-30, derived)
- Area: connected component >= TARGET_HA ha
- Region: Puerto López – Puerto Gaitán corridor (Oxisol domain)

Outputs:
- analyses/06_virtual_erw_field/field.geojson  — selected polygon (WGS84)
- analyses/06_virtual_erw_field/candidates.geojson — top-10 candidates with stats

Contigüidad decision (undocumented in plan; David did not specify a threshold):
- We find connected components of WorldCover class-40 pixels with slope < 3°.
- A component is a candidate if its area >= MIN_COMPONENT_HA (500 ha).
- We then select the largest component that is >= TARGET_HA.
- If none exists at 100 m aggregation, we lower to the largest available and document.
- This threshold is documented here and in the analysis README.

Data sources (both CC-licensed, no credentials required):
- WorldCover S3: s3://esa-worldcover/v200/2021/map/ (HTTP, COG)
- Copernicus DEM S3: s3://copernicus-dem-30m/ (HTTP, COG)

Run:
    uv run python analyses/06_virtual_erw_field/select_polygon.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

# ──────────────────────────────────────────────────────────────────────────────
# Parameters
# ──────────────────────────────────────────────────────────────────────────────

# Search bounding box (WGS84): Puerto López–Puerto Gaitán corridor
SEARCH_BBOX = {
    "lon_min": -73.5,
    "lat_min": 3.5,
    "lon_max": -71.5,
    "lat_max": 5.0,
}

TARGET_HA = 5000.0
MIN_COMPONENT_HA = 500.0
MAX_SLOPE_DEG = 3.0
WORLDCOVER_CLASS_CROPLAND = 40
# Working resolution for search (metres) — we aggregate WorldCover 10 m → 100 m
SEARCH_RESOLUTION_M = 100.0

# WorldCover 2021 v200 — S3 COG tile URL template
# Tiles are 3°×3°, named by lower-left corner at 3° increments.
# Lower-left lat = floor(lat/3)*3, lower-left lon = floor(lon/3)*3
WORLDCOVER_S3_URL = (
    "https://esa-worldcover.s3.eu-central-1.amazonaws.com"
    "/v200/2021/map/ESA_WorldCover_10m_2021_v200_{tile}_Map.tif"
)

# Copernicus DEM GLO-30 — S3 COG tile URL template
# Tiles are 1°×1°, named by lower-left corner: N04_00 W072_00
COPDEM_S3_URL = (
    "https://copernicus-dem-30m.s3.amazonaws.com"
    "/Copernicus_DSM_COG_10_{NS}{lat_deg:02d}_00_{EW}{lon_deg:03d}_00_DEM"
    "/Copernicus_DSM_COG_10_{NS}{lat_deg:02d}_00_{EW}{lon_deg:03d}_00_DEM.tif"
)

OUT_DIR = REPO_ROOT / "analyses" / "06_virtual_erw_field"
FIELD_GEOJSON = OUT_DIR / "field.geojson"
CANDIDATES_GEOJSON = OUT_DIR / "candidates.geojson"

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


def worldcover_tile_name(lat: float, lon: float) -> str:
    """Return WorldCover tile name for a point (lower-left 3° tile)."""
    lat_ll = int(np.floor(lat / 3) * 3)
    lon_ll = int(np.floor(lon / 3) * 3)
    ns = "N" if lat_ll >= 0 else "S"
    ew = "E" if lon_ll >= 0 else "W"
    return f"{ns}{abs(lat_ll):02d}{ew}{abs(lon_ll):03d}"


def worldcover_tile_url(tile_name: str) -> str:
    return WORLDCOVER_S3_URL.format(tile=tile_name)


def copdem_tile_url(lat: int, lon: int) -> str:
    """Return Copernicus DEM tile URL for integer lower-left lat/lon."""
    ns = "N" if lat >= 0 else "S"
    ew = "W" if lon < 0 else "E"
    return COPDEM_S3_URL.format(NS=ns, lat_deg=abs(lat), EW=ew, lon_deg=abs(lon))


def tiles_for_bbox(
    lat_min: float, lat_max: float, lon_min: float, lon_max: float, step: int
) -> list[tuple[int, int]]:
    """Return (lat, lon) lower-left corners at `step`-degree increments covering the bbox."""
    lats = range(int(np.floor(lat_min / step) * step), int(np.ceil(lat_max)), step)
    lons = range(int(np.floor(lon_min / step) * step), int(np.ceil(lon_max)), step)
    return [(la, lo) for la in lats for lo in lons]


def meters_per_degree(lat_deg: float) -> tuple[float, float]:
    """Return (m_per_lat_deg, m_per_lon_deg) at given latitude."""
    lat_rad = np.radians(lat_deg)
    m_per_lat = 111132.92 - 559.82 * np.cos(2 * lat_rad) + 1.175 * np.cos(4 * lat_rad)
    m_per_lon = 111412.84 * np.cos(lat_rad) - 93.5 * np.cos(3 * lat_rad)
    return m_per_lat, m_per_lon


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────


def main() -> None:
    import rasterio
    import rasterio.merge
    import rasterio.transform
    import rasterio.warp
    import rasterio.windows
    from rasterio.enums import Resampling
    from scipy.ndimage import label as ndlabel
    from shapely.geometry import mapping, shape

    print("=== ERW polygon selection — Altillanura, Meta, Colombia ===")
    print(f"Search bbox: {SEARCH_BBOX}")
    print(f"Target: {TARGET_HA} ha contiguous cropland, slope < {MAX_SLOPE_DEG}°")

    lat_c = (SEARCH_BBOX["lat_min"] + SEARCH_BBOX["lat_max"]) / 2
    m_per_lat, m_per_lon = meters_per_degree(lat_c)

    # ── 1. WorldCover: identify which 3°×3° tiles we need ────────────────────
    wc_tile_corners = tiles_for_bbox(
        SEARCH_BBOX["lat_min"],
        SEARCH_BBOX["lat_max"],
        SEARCH_BBOX["lon_min"],
        SEARCH_BBOX["lon_max"],
        step=3,
    )
    wc_tile_names = {worldcover_tile_name(la + 1.5, lo + 1.5) for la, lo in wc_tile_corners}
    print(f"\nWorldCover tiles: {sorted(wc_tile_names)}")

    # ── 2. Read WorldCover at reduced resolution (windowed COG read) ──────────
    # We need cell_size in degrees for resampling
    cell_deg_lat = SEARCH_RESOLUTION_M / m_per_lat
    cell_deg_lon = SEARCH_RESOLUTION_M / m_per_lon

    nx = int(round((SEARCH_BBOX["lon_max"] - SEARCH_BBOX["lon_min"]) / cell_deg_lon))
    ny = int(round((SEARCH_BBOX["lat_max"] - SEARCH_BBOX["lat_min"]) / cell_deg_lat))
    print(f"\nSearch grid at {SEARCH_RESOLUTION_M} m: {nx}×{ny} cells ({nx * ny:,})")

    cropland_mask = np.zeros((ny, nx), dtype=bool)
    wc_ok = False

    for tile_name in sorted(wc_tile_names):
        url = worldcover_tile_url(tile_name)
        vsicurl = f"/vsicurl/{url}"
        print(f"  WorldCover tile {tile_name}: {url}")
        try:
            with rasterio.open(vsicurl) as src:
                # Build window for our search bbox
                win = rasterio.windows.from_bounds(
                    SEARCH_BBOX["lon_min"],
                    SEARCH_BBOX["lat_min"],
                    SEARCH_BBOX["lon_max"],
                    SEARCH_BBOX["lat_max"],
                    transform=src.transform,
                )
                # Read at reduced resolution
                data = src.read(
                    1,
                    window=win,
                    out_shape=(ny, nx),
                    resampling=Resampling.nearest,
                )
                cropland_mask |= data == WORLDCOVER_CLASS_CROPLAND
                wc_ok = True
                print(f"    → {np.sum(cropland_mask):,} cropland cells so far")
        except Exception as exc:
            print(f"    ⚠ Could not read {tile_name}: {exc}")

    if not wc_ok:
        print("ERROR: Could not read any WorldCover tile.")
        sys.exit(1)

    cropland_area_ha = np.sum(cropland_mask) * (SEARCH_RESOLUTION_M / 100) ** 2
    print(f"\nTotal cropland in search bbox: {cropland_area_ha:,.0f} ha")

    # ── 3. DEM / slope: read Copernicus DEM 1°×1° tiles ─────────────────────
    dem_tiles = tiles_for_bbox(
        SEARCH_BBOX["lat_min"],
        SEARCH_BBOX["lat_max"],
        SEARCH_BBOX["lon_min"],
        SEARCH_BBOX["lon_max"],
        step=1,
    )
    print(f"\nCopernicus DEM tiles needed: {len(dem_tiles)}")

    # Accumulate DEM at same grid
    elev_sum = np.zeros((ny, nx), dtype=np.float32)
    elev_count = np.zeros((ny, nx), dtype=np.int16)

    for lat_ll, lon_ll in dem_tiles:
        url = copdem_tile_url(lat_ll, lon_ll)
        vsicurl = f"/vsicurl/{url}"
        try:
            with rasterio.open(vsicurl) as src:
                win = rasterio.windows.from_bounds(
                    SEARCH_BBOX["lon_min"],
                    SEARCH_BBOX["lat_min"],
                    SEARCH_BBOX["lon_max"],
                    SEARCH_BBOX["lat_max"],
                    transform=src.transform,
                )
                data = src.read(
                    1,
                    window=win,
                    out_shape=(ny, nx),
                    resampling=Resampling.bilinear,
                ).astype(np.float32)
                valid = data > -9000
                elev_sum[valid] += data[valid]
                elev_count[valid] += 1
        except Exception as exc:
            print(f"  ⚠ DEM tile ({lat_ll},{lon_ll}): {exc}")

    # Compute mean elevation
    elev = np.where(elev_count > 0, elev_sum / elev_count, np.nan)

    # Slope from central differences (degrees)
    # dy in metres (latitudinal), dx in metres (longitudinal)
    dy_m = SEARCH_RESOLUTION_M
    dx_m = SEARCH_RESOLUTION_M
    dz_dy = np.gradient(elev, dy_m, axis=0)
    dz_dx = np.gradient(elev, dx_m, axis=1)
    slope_deg = np.degrees(np.arctan(np.sqrt(dz_dx**2 + dz_dy**2)))

    low_slope = slope_deg < MAX_SLOPE_DEG
    low_slope[np.isnan(slope_deg)] = False

    print(f"Cells with slope < {MAX_SLOPE_DEG}°: {np.sum(low_slope):,}")

    # ── 4. Combined mask and connected components ─────────────────────────────
    combined = cropland_mask & low_slope
    n_combined = np.sum(combined)
    combined_ha = n_combined * (SEARCH_RESOLUTION_M / 100) ** 2
    print(f"Cropland + slope < {MAX_SLOPE_DEG}°: {n_combined:,} cells = {combined_ha:,.0f} ha")

    # Connected components (4-connectivity)
    labeled, n_components = ndlabel(combined)
    print(f"Connected components: {n_components}")

    # Component stats
    component_sizes = np.bincount(labeled.ravel())
    component_ha = component_sizes * (SEARCH_RESOLUTION_M / 100) ** 2

    # Candidates: components >= MIN_COMPONENT_HA
    candidate_ids = np.where(component_ha >= MIN_COMPONENT_HA)[0]
    candidate_ids = candidate_ids[candidate_ids > 0]  # exclude background (0)

    print(f"Candidate components (>= {MIN_COMPONENT_HA} ha): {len(candidate_ids)}")
    if len(candidate_ids) == 0:
        print("ERROR: No candidate components found. Check the search bbox and data.")
        sys.exit(1)

    # Sort by size descending
    candidate_ids = candidate_ids[np.argsort(-component_ha[candidate_ids])]
    top10 = candidate_ids[:10]

    # ── 5. Build GeoJSON features for top candidates ─────────────────────────
    from rasterio.features import shapes as rio_shapes

    # Affine transform for our search grid
    transform = rasterio.transform.from_bounds(
        SEARCH_BBOX["lon_min"],
        SEARCH_BBOX["lat_min"],
        SEARCH_BBOX["lon_max"],
        SEARCH_BBOX["lat_max"],
        nx,
        ny,
    )

    candidate_features = []
    selected_id = None

    for cid in top10:
        mask_c = (labeled == cid).astype(np.uint8)
        geoms = list(rio_shapes(mask_c, mask=mask_c, transform=transform))
        if not geoms:
            continue
        # Merge all polygons for this component into one multipolygon
        from shapely.ops import unary_union

        polys = [shape(g) for g, _ in geoms]
        geom = unary_union(polys)

        ha = component_ha[cid]
        feature = {
            "type": "Feature",
            "properties": {
                "component_id": int(cid),
                "area_ha": float(ha),
                "n_cells": int(component_sizes[cid]),
                "meets_target": ha >= TARGET_HA,
                "slope_criterion": f"< {MAX_SLOPE_DEG}°",
                "worldcover_class": WORLDCOVER_CLASS_CROPLAND,
                "search_resolution_m": SEARCH_RESOLUTION_M,
            },
            "geometry": mapping(geom),
        }
        candidate_features.append(feature)

        if selected_id is None and ha >= TARGET_HA:
            selected_id = cid
            print(f"\n✓ Selected polygon: component {cid}, {ha:,.0f} ha")

    if selected_id is None:
        # Take the largest available
        selected_id = top10[0]
        ha_sel = component_ha[selected_id]
        print(
            f"\n⚠ No component >= {TARGET_HA} ha found at {SEARCH_RESOLUTION_M} m resolution.\n"
            f"  Largest candidate: {ha_sel:,.0f} ha (component {selected_id}).\n"
            f"  Proceeding with largest available. Document in README as limitation."
        )

    # ── 6. Save candidates GeoJSON ────────────────────────────────────────────
    # Convert numpy scalars to native Python types for JSON serialisation
    def _json_default(obj: object) -> object:
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

    candidates_fc = {"type": "FeatureCollection", "features": candidate_features}
    CANDIDATES_GEOJSON.write_text(json.dumps(candidates_fc, indent=2, default=_json_default))
    print(f"\nCandidates saved: {CANDIDATES_GEOJSON}")

    # ── 7. Save selected field.geojson ────────────────────────────────────────
    selected = next(f for f in candidate_features if f["properties"]["component_id"] == selected_id)
    selected["properties"]["status"] = "selected"
    selected["properties"]["oxisol_criterion"] = (
        "pending — SoilGrids/IGAC Oxisol/Ferralsol verification required"
    )
    selected["properties"]["contiguity_rule"] = (
        f"connected component (4-connectivity) of WorldCover class {WORLDCOVER_CLASS_CROPLAND} "
        f"at {SEARCH_RESOLUTION_M} m with slope < {MAX_SLOPE_DEG}°"
    )
    selected["properties"]["data_sources"] = [
        "ESA WorldCover 2021 v200 (CC BY 4.0)",
        "Copernicus DEM GLO-30 (Copernicus WorldDEM-30 Licence)",
    ]

    field_fc = {"type": "FeatureCollection", "features": [selected]}
    FIELD_GEOJSON.write_text(json.dumps(field_fc, indent=2, default=_json_default))
    print(f"Field polygon saved: {FIELD_GEOJSON}")

    # ── 8. Print summary ──────────────────────────────────────────────────────
    props = selected["properties"]
    print("\n" + "=" * 60)
    print("POLYGON CANDIDATE SUMMARY")
    print("=" * 60)
    print(f"Area:        {props['area_ha']:,.0f} ha")
    print(f"Cells:       {props['n_cells']:,} at {SEARCH_RESOLUTION_M} m")
    print(f"Slope:       {props['slope_criterion']} (Copernicus DEM GLO-30)")
    print(f"Cropland:    WorldCover 2021 v200 class {WORLDCOVER_CLASS_CROPLAND}")
    print(f"Oxisol:      {props['oxisol_criterion']}")
    print(f"Candidates:  {len(candidate_features)} (top {len(top10)} shown)")
    print(f"Output:      {FIELD_GEOJSON}")
    print("=" * 60)
    print("\nNext step: verify Oxisol criterion with SoilGrids (WRB Ferralsol),")
    print("then show polygon to David before proceeding to Phase 1.2.")


if __name__ == "__main__":
    main()
