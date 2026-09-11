"""
Conventional baseline routing: Dijkstra and A*.

Both algorithms run on the SAME dynamic, traffic-aware, multi-objective
edge cost (see cost.py) as the rest of the system - the only difference
between them and QuantumRoute's optimizer is the *search strategy*, not
the cost model. This is important for a fair benchmark: we are not
comparing "shortest path" vs "smart path", we're comparing "greedy
optimal single-path search" vs "population/annealing based route
selection over a cost landscape", using an identical cost function.

Dijkstra: classic single-source shortest path, guaranteed optimal for
non-negative edge weights (our costs are always >= 0, closed edges are
+inf and are simply never expanded).

A*: Dijkstra + an admissible geographic heuristic (great-circle distance
to the goal, converted into the same normalized cost units Dijkstra
uses) to prune the search space. Because the heuristic never
overestimates the true remaining cost (straight-line distance <= any
real road distance, and our normalized distance term is the dominant
lower bound), A* is still guaranteed optimal here, just faster.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import heapq
import networkx as nx

from app.routing.cost import CostWeights, compute_edge_cost, INF_COST
from app.routing.node_utils import haversine_m
from app.simulation.traffic import TrafficSnapshot


@dataclass
class RouteResult:
    algorithm: str
    found: bool
    node_path: List[int] = field(default_factory=list)
    coordinates: List[Tuple[float, float]] = field(default_factory=list)  # (lat, lon)
    total_distance_m: float = 0.0
    total_travel_time_sec: float = 0.0
    total_cost: float = 0.0
    num_edges: int = 0
    computation_time_ms: float = 0.0
    reason: Optional[str] = None


def _edge_weight_fn(G: nx.MultiDiGraph, traffic: Optional[TrafficSnapshot], weights: CostWeights):
    """Build a (u, v, edge_data_dict) -> cost function for a MultiDiGraph,
    picking the cheapest parallel edge between u and v (matches how
    networkx expects multigraph weight callables to behave)."""

    def weight(u, v, edge_dict):
        best = None
        for k, data in edge_dict.items():
            t = traffic.get(u, v, k) if traffic else None
            breakdown = compute_edge_cost(data, t, weights)
            if best is None or breakdown.total_cost < best:
                best = breakdown.total_cost
        return best if best is not None else INF_COST

    return weight


def _build_route_result(
    G: nx.MultiDiGraph,
    path: List[int],
    algorithm: str,
    traffic: Optional[TrafficSnapshot],
    weights: CostWeights,
    computation_time_ms: float,
) -> RouteResult:
    coords = [(G.nodes[n]["y"], G.nodes[n]["x"]) for n in path]
    total_distance = 0.0
    total_time = 0.0
    total_cost = 0.0

    for u, v in zip(path[:-1], path[1:]):
        edge_dict = G.get_edge_data(u, v)
        best_cost = None
        best_data = None
        best_key = 0
        for k, data in edge_dict.items():
            t = traffic.get(u, v, k) if traffic else None
            breakdown = compute_edge_cost(data, t, weights)
            if best_cost is None or breakdown.total_cost < best_cost:
                best_cost = breakdown.total_cost
                best_data = data
                best_key = k
        t = traffic.get(u, v, best_key) if traffic else None
        breakdown = compute_edge_cost(best_data, t, weights)
        total_distance += breakdown.distance_m
        total_time += breakdown.travel_time_sec
        total_cost += breakdown.total_cost

    return RouteResult(
        algorithm=algorithm,
        found=True,
        node_path=path,
        coordinates=coords,
        total_distance_m=round(total_distance, 2),
        total_travel_time_sec=round(total_time, 2),
        total_cost=round(total_cost, 6),
        num_edges=len(path) - 1,
        computation_time_ms=computation_time_ms,
    )


def dijkstra_route(
    G: nx.MultiDiGraph,
    source: int,
    target: int,
    traffic: Optional[TrafficSnapshot] = None,
    weights: Optional[CostWeights] = None,
) -> RouteResult:
    weights = weights or CostWeights()
    weight_fn = _edge_weight_fn(G, traffic, weights)

    start = time.perf_counter()
    try:
        path = nx.dijkstra_path(G, source, target, weight=weight_fn)
    except nx.NetworkXNoPath:
        elapsed = (time.perf_counter() - start) * 1000
        return RouteResult(algorithm="dijkstra", found=False,
                            computation_time_ms=round(elapsed, 3),
                            reason="No path exists between source and destination "
                                   "(graph disconnected or all connecting edges closed).")
    except nx.NodeNotFound as exc:
        elapsed = (time.perf_counter() - start) * 1000
        return RouteResult(algorithm="dijkstra", found=False,
                            computation_time_ms=round(elapsed, 3), reason=str(exc))
    elapsed = (time.perf_counter() - start) * 1000

    return _build_route_result(G, path, "dijkstra", traffic, weights, round(elapsed, 3))


def _astar_heuristic(G: nx.MultiDiGraph, target: int, weights: CostWeights):
    ty, tx = G.nodes[target]["y"], G.nodes[target]["x"]
    ref_distance_m = 500.0  # keep consistent with cost.py's _REF_DISTANCE_M

    def h_admissible(n, _target):
        # networkx calls heuristic(node, target); target is fixed to the
        # value we closed over, but we accept the arg to match the API.
        ny, nx_ = G.nodes[n]["y"], G.nodes[n]["x"]
        dist_m = haversine_m(ny, nx_, ty, tx)
        # Lower bound on remaining normalized distance-cost: each edge
        # contributes at most weights.distance * 1.0 per _REF_DISTANCE_M
        # meters, so the minimum possible remaining cost is
        # weights.distance * (dist_m / _REF_DISTANCE_M), which never
        # overestimates the true minimum sum of per-edge distance terms.
        return weights.distance * (dist_m / ref_distance_m)

    return h_admissible


def astar_route(
    G: nx.MultiDiGraph,
    source: int,
    target: int,
    traffic: Optional[TrafficSnapshot] = None,
    weights: Optional[CostWeights] = None,
) -> RouteResult:
    weights = weights or CostWeights()
    weight_fn = _edge_weight_fn(G, traffic, weights)
    heuristic = _astar_heuristic(G, target, weights)

    start = time.perf_counter()
    try:
        path = nx.astar_path(G, source, target, heuristic=heuristic, weight=weight_fn)
    except nx.NetworkXNoPath:
        elapsed = (time.perf_counter() - start) * 1000
        return RouteResult(algorithm="astar", found=False,
                            computation_time_ms=round(elapsed, 3),
                            reason="No path exists between source and destination "
                                   "(graph disconnected or all connecting edges closed).")
    except nx.NodeNotFound as exc:
        elapsed = (time.perf_counter() - start) * 1000
        return RouteResult(algorithm="astar", found=False,
                            computation_time_ms=round(elapsed, 3), reason=str(exc))
    elapsed = (time.perf_counter() - start) * 1000

    return _build_route_result(G, path, "astar", traffic, weights, round(elapsed, 3))
