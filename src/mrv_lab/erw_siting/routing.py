"""Road distance from every cell to its nearest rock source (plan F5, part 5.4).

Network: OSM truck roads (F3 classes) as an undirected graph whose nodes are line vertices (rounded
to 1 m, so lines sharing a vertex connect) and whose edges are segment lengths. One multi-source
Dijkstra (``scipy.sparse.csgraph``) from all source nodes gives, for every node, the shortest road
distance to any source and which source it is.

Distance of a cell (D-47): ``road_km`` = cell-to-road link (straight, "last mile") + network
distance + the source's access distance to the rock (``access_km``, F3). Distance only, no
travel time.
Cells and sources snap to the largest connected road component (isolated fragments are skipped;
the extra straight distance counts as last mile). Two scenarios: ``apta`` (base) and
``apta_mixta`` (sensitivity, D-40). Unreachable cells get NaN.
"""

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components, dijkstra
from scipy.spatial import cKDTree
from shapely.geometry import LineString

SCENARIOS: dict[str, tuple[str, ...]] = {"apta": ("Apta",), "apta_mixta": ("Apta", "Mixta")}


class RoadGraph:
    """Undirected road graph built from line geometries (metres)."""

    def __init__(self, lines: gpd.GeoSeries):
        coords, starts, ends = [], [], []
        index: dict[tuple[float, float], int] = {}
        for geom in lines.explode(index_parts=False):
            pts = [(round(x), round(y)) for x, y in geom.coords]
            ids = []
            for p in pts:
                if p not in index:
                    index[p] = len(coords)
                    coords.append(p)
                ids.append(index[p])
            starts.extend(ids[:-1])
            ends.extend(ids[1:])
        self.xy = np.asarray(coords, dtype="float64")
        a, b = np.asarray(starts), np.asarray(ends)
        keep = a != b
        a, b = a[keep], b[keep]
        length = np.hypot(*(self.xy[a] - self.xy[b]).T)
        n = len(self.xy)
        self.matrix = coo_matrix(
            (np.r_[length, length], (np.r_[a, b], np.r_[b, a])), shape=(n, n)
        ).tocsr()
        # Truck-road subsets leave isolated fragments (linked to the main network only through
        # excluded classes). Cells and sources snap to the largest component only (D-47).
        _, labels = connected_components(self.matrix, directed=False)
        self.main_nodes = np.flatnonzero(labels == np.bincount(labels).argmax())
        self.tree = cKDTree(self.xy[self.main_nodes])

    def snap(self, x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Nearest node and straight distance (m) for each point."""
        dist, idx = self.tree.query(np.column_stack([x, y]))
        return self.main_nodes[idx], dist

    def path(self, predecessors: np.ndarray, node: int) -> LineString | None:
        """Road geometry from ``node`` back to its source."""
        nodes = [node]
        while predecessors[nodes[-1]] >= 0:
            nodes.append(predecessors[nodes[-1]])
        return LineString(self.xy[nodes]) if len(nodes) > 1 else None


def nearest_sources(
    graph: RoadGraph, cells: gpd.GeoDataFrame, sources: gpd.GeoDataFrame, scenario: str
) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    """Nearest source by road for every cell; also returns predecessors and cell nodes."""
    chosen = sources[sources["final_class"].isin(SCENARIOS[scenario])].reset_index(drop=True)
    src_nodes, src_snap = graph.snap(chosen.geometry.x.to_numpy(), chosen.geometry.y.to_numpy())
    unique_nodes, first = np.unique(src_nodes, return_index=True)
    dist, pred, origin = dijkstra(
        graph.matrix,
        directed=False,
        indices=unique_nodes,
        min_only=True,
        return_predecessors=True,
    )
    cell_nodes, cell_snap = graph.snap(
        cells["x_center_m"].to_numpy(), cells["y_center_m"].to_numpy()
    )
    node_to_source = dict(zip(unique_nodes, first, strict=True))
    src_idx = np.array([node_to_source.get(o, -1) for o in origin[cell_nodes]])
    reachable = np.isfinite(dist[cell_nodes]) & (src_idx >= 0)
    safe = np.where(reachable, src_idx, 0)
    road_m = (
        cell_snap + dist[cell_nodes] + src_snap[safe] + chosen["access_km"].to_numpy()[safe] * 1000
    )
    straight_m = np.hypot(
        cells["x_center_m"].to_numpy() - chosen.geometry.x.to_numpy()[safe],
        cells["y_center_m"].to_numpy() - chosen.geometry.y.to_numpy()[safe],
    )
    table = pd.DataFrame(
        {
            "cell_id": cells["cell_id"].to_numpy(),
            "scenario": scenario,
            "rock_source_id": np.where(reachable, chosen["rock_source_id"].to_numpy()[safe], None),
            "road_km": np.where(reachable, road_m / 1000, np.nan),
            "straight_km": np.where(reachable, straight_m / 1000, np.nan),
            "last_mile_km": cell_snap / 1000,
        }
    )
    return table, pred, cell_nodes
