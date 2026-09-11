"""
Candidate route generation.

Rather than committing to a single shortest path before optimization,
we generate several *distinct, loopless* candidate routes between
source and target using Yen's k-shortest-paths algorithm (networkx's
`shortest_simple_paths`, which implements Yen's algorithm). This gives
the downstream QUBO/optimizer stage something real to choose between -
without this step, "QUBO route selection" would be selecting among a
set of size one, which would be dishonest.

Why Yen's algorithm specifically (vs. random edge-weight perturbation):
- It guarantees the k returned paths are loopless and strictly ordered
  by cost, which is important for defensibility ("candidate route #1
  actually is the cheapest, #2 is the next cheapest distinct route",
  not an arbitrary perturbation).
- It's deterministic given a fixed graph/weights, which matters for
  reproducible SIH demos.

Trade-off (documented in docs/limitations.md): Yen's algorithm is
O(k * n * (m + n log n)) and can be slow on very large graphs with a
large k. For our small demo graph and k <= ~8 this is fast (see
benchmark numbers in docs/benchmarking.md); at true city scale it would
need to be replaced or bounded more aggressively.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from itertools import islice
from typing import List, Optional, Tuple

import networkx as nx

from app.routing.baseline import _edge_weight_fn, _build_route_result, RouteResult
from app.routing.cost import CostWeights
from app.simulation.traffic import TrafficSnapshot


def _flatten_to_digraph(G: nx.MultiDiGraph, weight_fn) -> nx.DiGraph:
    """
    networkx's shortest_simple_paths (Yen's algorithm) does not support
    MultiDiGraph. We flatten to a simple DiGraph, keeping only the
    cheapest parallel edge between any (u, v) pair, with its cost baked
    in as a static 'weight' attribute. This is safe because our cost
    function is evaluated once per traffic snapshot (it doesn't change
    during the search), so precomputing it is equivalent to calling the
    weight function live.
    """
    D = nx.DiGraph()
    D.add_nodes_from(G.nodes(data=True))
    for u in G.nodes():
        for v, edge_dict in G.adj[u].items():
            w = weight_fn(u, v, edge_dict)
            if w == float("inf"):
                continue
            if D.has_edge(u, v):
                if w < D[u][v]["weight"]:
                    D[u][v]["weight"] = w
            else:
                D.add_edge(u, v, weight=w)
    return D


@dataclass
class CandidateSet:
    routes: List[RouteResult] = field(default_factory=list)
    generation_time_ms: float = 0.0
    method: str = "yen_k_shortest_paths"
    requested_k: int = 0
    returned_k: int = 0


def generate_candidate_routes(
    G: nx.MultiDiGraph,
    source: int,
    target: int,
    traffic: Optional[TrafficSnapshot] = None,
    weights: Optional[CostWeights] = None,
    k: int = 5,
) -> CandidateSet:
    """
    Return up to `k` distinct loopless candidate routes between source
    and target, ordered from cheapest to most expensive under the
    current dynamic multi-objective cost function.
    """
    weights = weights or CostWeights()
    weight_fn = _edge_weight_fn(G, traffic, weights)
    D = _flatten_to_digraph(G, weight_fn)

    start = time.perf_counter()
    routes: List[RouteResult] = []
    try:
        path_generator = nx.shortest_simple_paths(D, source, target, weight="weight")
        for path in islice(path_generator, k):
            elapsed_so_far = (time.perf_counter() - start) * 1000
            route = _build_route_result(
                G, path, "candidate", traffic, weights, round(elapsed_so_far, 3)
            )
            routes.append(route)
    except nx.NetworkXNoPath:
        pass
    except nx.NodeNotFound:
        pass

    elapsed = (time.perf_counter() - start) * 1000
    return CandidateSet(
        routes=routes,
        generation_time_ms=round(elapsed, 3),
        requested_k=k,
        returned_k=len(routes),
    )
