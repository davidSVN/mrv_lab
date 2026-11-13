"""Small geometry helpers shared by the ERW siting layers."""

import geopandas as gpd
from shapely.geometry import GeometryCollection, MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry


def polygon_parts(geom: BaseGeometry) -> BaseGeometry:
    """Keep only the polygon parts of a geometry (``make_valid`` can return lines or points too)."""
    if isinstance(geom, Polygon | MultiPolygon):
        return geom
    if isinstance(geom, GeometryCollection):
        parts = [g for g in geom.geoms if isinstance(g, Polygon | MultiPolygon)]
        polys = [p for g in parts for p in (g.geoms if isinstance(g, MultiPolygon) else [g])]
        return MultiPolygon(polys) if polys else Polygon()
    return Polygon()


def repair_polygons(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Make geometries valid, keep polygon parts only and drop empty rows."""
    gdf = gdf.copy()
    gdf["geometry"] = gdf.geometry.make_valid().map(polygon_parts)
    return gdf[~gdf.geometry.is_empty]
