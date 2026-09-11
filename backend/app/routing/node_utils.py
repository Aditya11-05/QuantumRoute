"""
Small geographic helpers: nearest-node lookup and haversine distance.
Kept dependency-free (no scipy/sklearn KDTree) since our demo graphs are
small (tens to a few thousand nodes) - a linear scan is fast enough and
easy to reason about/test. For a full-city graph this would be swapped
for a KD-tree (osmnx.distance.nearest_nodes uses one internally), and
that swap point is called out in docs/limitations.
"""
from __future__ import annotations

import math
from typing import Tuple

import networkx as nx


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in meters between two lat/lon points."""
    R = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(min(1.0, math.sqrt(a)))


def nearest_node(G: nx.MultiDiGraph, lat: float, lon: float) -> Tuple[int, float]:
    """
    Return (node_id, distance_meters) of the graph node closest to
    (lat, lon). Raises ValueError if the graph has no nodes.
    """
    if G.number_of_nodes() == 0:
        raise ValueError("Graph has no nodes")

    best_node = None
    best_dist = float("inf")
    for nid, data in G.nodes(data=True):
        d = haversine_m(lat, lon, data["y"], data["x"])
        if d < best_dist:
            best_dist = d
            best_node = nid
    return best_node, best_dist


def bounding_box(G: nx.MultiDiGraph) -> dict:
    lats = [d["y"] for _, d in G.nodes(data=True)]
    lons = [d["x"] for _, d in G.nodes(data=True)]
    return {
        "min_lat": min(lats), "max_lat": max(lats),
        "min_lon": min(lons), "max_lon": max(lons),
    }
