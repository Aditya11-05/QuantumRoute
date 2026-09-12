"""
map_matching.py — Sensor -> OSM edge spatial matching.

Implements a real nearest-edge matching method (NOT arbitrary assignment):
for each traffic sensor coordinate, project it onto every candidate OSM
edge geometry within a search radius and pick the edge with the minimum
perpendicular distance. This is the standard "nearest road segment"
map-matching baseline (a simplified, non-HMM version of the approach
used in tools like Leuven Map Matching / OSRM's match service).

This module performs NO computation until called with real inputs
(an OSMnx graph + a real sensor coordinate table). It is written now so
it's ready the moment scripts/download_osm_network.py and
scripts/download_traffic_data.py have both been run locally.

Method:
    1. Build a spatial index (KD-tree in projected UTM coordinates, so
       distances are true meters, not degrees) over all OSM edge geometries,
       sampled at fixed intervals along each edge.
    2. For each sensor, query the k nearest sampled points, recover their
       parent edge, and compute exact perpendicular distance to that edge's
       full LineString geometry (via shapely).
    3. Accept the match only if distance <= max_distance_m (default 50m,
       configurable). Sensors beyond this are marked NO_MATCH — never
       silently forced onto an arbitrary edge.

Output columns: sensor_id, latitude, longitude, matched_u, matched_v,
matched_key, distance_m, status ("MATCHED" | "NO_MATCH").
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import math


@dataclass
class MatchResult:
    sensor_id: str
    latitude: float
    longitude: float
    matched_u: Optional[int]
    matched_v: Optional[int]
    matched_key: Optional[int]
    distance_m: Optional[float]
    status: str  # "MATCHED" or "NO_MATCH"


def match_sensors_to_graph(G, sensors: list[dict], max_distance_m: float = 50.0,
                            sample_spacing_m: float = 5.0) -> list[MatchResult]:
    """
    G: an OSMnx graph loaded via ox.load_graphml(...), already projected
       to a metric CRS via ox.project_graph(G) BEFORE calling this function.
       (Projecting first is required for distance_m to be meaningful —
       lat/lon degrees are not uniform distances.)
    sensors: list of dicts with keys 'sensor_id', 'latitude', 'longitude'
             (WGS84 degrees, as published in the raw sensor location file).
    max_distance_m: matches farther than this are rejected as NO_MATCH.
    sample_spacing_m: how densely to sample along edge geometries when
             building the search index (smaller = more accurate, slower).

    Returns one MatchResult per input sensor. Does not mutate G.
    """
    import numpy as np
    from scipy.spatial import cKDTree
    from shapely.geometry import Point, LineString
    from pyproj import Transformer
    import osmnx as ox

    # Recover the graph's projected CRS (set by ox.project_graph) to
    # transform sensor lat/lon into the same metric coordinate system.
    graph_crs = G.graph.get("crs")
    if graph_crs is None:
        raise ValueError(
            "Graph has no CRS — call ox.project_graph(G) before matching, "
            "so edge geometry is in meters, not degrees."
        )
    to_metric = Transformer.from_crs("EPSG:4326", graph_crs, always_xy=True)

    # 1. Sample points along every edge geometry, remembering (u, v, key).
    sample_pts = []
    sample_owner = []  # parallel list of (u, v, key)
    edge_geoms = {}  # (u, v, key) -> LineString, for exact distance later

    for u, v, key, data in G.edges(keys=True, data=True):
        geom = data.get("geometry")
        if geom is None:
            # No explicit geometry: OSMnx default is a straight line between nodes.
            p1 = (G.nodes[u]["x"], G.nodes[u]["y"])
            p2 = (G.nodes[v]["x"], G.nodes[v]["y"])
            geom = LineString([p1, p2])
        edge_geoms[(u, v, key)] = geom

        length = geom.length
        n_samples = max(2, int(length // sample_spacing_m) + 1)
        for i in range(n_samples):
            pt = geom.interpolate(i / (n_samples - 1), normalized=True)
            sample_pts.append((pt.x, pt.y))
            sample_owner.append((u, v, key))

    if not sample_pts:
        raise ValueError("Graph has no edges to match against.")

    tree = cKDTree(np.array(sample_pts))

    results = []
    for s in sensors:
        x, y = to_metric.transform(s["longitude"], s["latitude"])
        # Query a handful of nearest sample points; the true nearest edge
        # might not be the single nearest sample point's owner if sampling
        # is coarse, so we check the top-k candidates' exact geometry.
        k = 8
        dists, idxs = tree.query((x, y), k=min(k, len(sample_pts)))
        idxs = np.atleast_1d(idxs)

        candidate_edges = {sample_owner[i] for i in idxs}
        best_edge = None
        best_dist = math.inf
        sensor_pt = Point(x, y)
        for edge_id in candidate_edges:
            d = edge_geoms[edge_id].distance(sensor_pt)
            if d < best_dist:
                best_dist = d
                best_edge = edge_id

        if best_edge is not None and best_dist <= max_distance_m:
            u, v, key = best_edge
            results.append(MatchResult(
                sensor_id=s["sensor_id"], latitude=s["latitude"], longitude=s["longitude"],
                matched_u=u, matched_v=v, matched_key=key,
                distance_m=round(float(best_dist), 2), status="MATCHED",
            ))
        else:
            results.append(MatchResult(
                sensor_id=s["sensor_id"], latitude=s["latitude"], longitude=s["longitude"],
                matched_u=None, matched_v=None, matched_key=None,
                distance_m=round(float(best_dist), 2) if best_edge else None,
                status="NO_MATCH",
            ))

    return results


def summarize_matches(results: list[MatchResult]) -> dict:
    n = len(results)
    matched = [r for r in results if r.status == "MATCHED"]
    return {
        "total_sensors": n,
        "matched": len(matched),
        "no_match": n - len(matched),
        "match_rate_pct": round(100.0 * len(matched) / n, 2) if n else 0.0,
        "mean_distance_m": round(sum(r.distance_m for r in matched) / len(matched), 2) if matched else None,
        "max_distance_m": round(max((r.distance_m for r in matched), default=0.0), 2),
    }
