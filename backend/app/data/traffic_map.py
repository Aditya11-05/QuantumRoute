"""Build a transparent map-ready view of the current traffic snapshot.

Research-mode traffic segments are REAL_HISTORICAL only.  This module does
not interpolate or fabricate traffic for unobserved OSM edges.
"""
from __future__ import annotations

from typing import Any

import networkx as nx
from shapely import wkt

from app.simulation.traffic import TrafficSnapshot


def _edge_coordinates(G: nx.MultiDiGraph, u: int, v: int, data: dict[str, Any]):
    geometry = data.get("geometry")

    if geometry is not None:
        try:
            if hasattr(geometry, "coords"):
                return [[round(float(lat), 7), round(float(lon), 7)] for lon, lat in geometry.coords]
            if isinstance(geometry, str):
                parsed = wkt.loads(geometry)
                return [[round(float(lat), 7), round(float(lon), 7)] for lon, lat in parsed.coords]
        except Exception:
            # Fall back to node coordinates rather than dropping an observed edge.
            pass

    udata = G.nodes[u]
    vdata = G.nodes[v]
    return [
        [round(float(udata["y"]), 7), round(float(udata["x"]), 7)],
        [round(float(vdata["y"]), 7), round(float(vdata["x"]), 7)],
    ]


def build_traffic_map_segments(
    G: nx.MultiDiGraph,
    snapshot: TrafficSnapshot,
) -> dict[str, Any]:
    """Return only edges with observed traffic in the supplied snapshot."""
    segments: list[dict[str, Any]] = []

    for (u, v, key), state in snapshot.states.items():
        if not G.has_edge(u, v, key):
            continue

        data = G[u][v][key]
        highway = data.get("highway")
        if isinstance(highway, (list, tuple, set)):
            highway = str(next(iter(highway), "unknown"))
        else:
            highway = str(highway or "unknown")

        segments.append(
            {
                "u": int(u),
                "v": int(v),
                "key": int(key),
                "coordinates": _edge_coordinates(G, u, v, data),
                "speed_kmh": round(float(state.current_speed_kmh), 3),
                "congestion": round(float(state.congestion_level), 6),
                "highway": highway,
                "provenance": "REAL_HISTORICAL",
            }
        )

    segments.sort(key=lambda item: item["congestion"], reverse=True)

    network_edges = G.number_of_edges()
    observed_edges = len(segments)
    mean_speed = (
        sum(item["speed_kmh"] for item in segments) / observed_edges
        if observed_edges
        else None
    )
    mean_congestion = (
        sum(item["congestion"] for item in segments) / observed_edges
        if observed_edges
        else None
    )

    return {
        "provenance": "REAL_HISTORICAL",
        "observed_edges": observed_edges,
        "network_edges": network_edges,
        "coverage_pct": round(100.0 * observed_edges / network_edges, 4) if network_edges else 0.0,
        "mean_speed_kmh": round(mean_speed, 3) if mean_speed is not None else None,
        "mean_congestion": round(mean_congestion, 6) if mean_congestion is not None else None,
        "segments": segments,
    }
