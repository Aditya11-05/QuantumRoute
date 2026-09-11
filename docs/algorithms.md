# Algorithms

## Dijkstra's algorithm

**What it does:** finds the minimum-cost path from a source node to a
target node in a graph with non-negative edge weights.

**How QuantumRoute uses it:** `app/routing/baseline.py::dijkstra_route`
calls `networkx.dijkstra_path` with a *callable* weight function
(`_edge_weight_fn`) that evaluates our multi-objective cost (see
`algorithms.md` → cost function below) for every edge, using the
current traffic snapshot. This means Dijkstra here is not "shortest
distance" — it is "cheapest under whatever cost function and traffic
conditions are currently active." It is still the *conventional
baseline* because its search strategy is the classic greedy
priority-queue expansion with no heuristic guidance.

**Guarantee:** optimal for any graph with non-negative edge weights.
Our cost function is always ≥ 0 (closed roads get cost `+inf` and are
simply never expanded), so the guarantee holds.

**Complexity:** O((V + E) log V) with a binary heap, where V = nodes,
E = edges. On our 81-node/270-edge demo graph this is sub-millisecond;
see `docs/benchmarking.md` for measured numbers.

## A* search

**What it does:** Dijkstra plus a *heuristic* function `h(n)` that
estimates the remaining cost from node `n` to the target, used to
prioritize which nodes to expand next. If `h` never overestimates the
true remaining cost (i.e., it's *admissible*), A* is guaranteed to find
the same optimal path as Dijkstra, typically visiting fewer nodes.

**Our heuristic:** `weights.distance * (haversine_distance(n, target) /
REF_DISTANCE_M)`. This is a lower bound on the true remaining
*distance* component of cost, because straight-line (great-circle)
distance is always ≤ any real road distance, and the distance term is
one additively non-negative component of our total cost. We do NOT
include the travel-time or congestion components in the heuristic
lower bound, because those depend on live traffic and cannot be
lower-bounded purely geographically without risking inadmissibility.

**Verified in tests:** `tests/unit/test_baseline.py::
test_astar_matches_dijkstra_optimal_cost` runs both algorithms across
all 6 traffic scenarios and asserts their total costs match to 1e-6 -
this is the actual proof that our heuristic is admissible in practice,
not just an assertion in a comment.

## Yen's k-shortest-paths algorithm (candidate route generation)

**What it does:** given a graph, source, target, and k, returns the k
distinct loopless paths with the lowest total cost, in ascending
order.

**How QuantumRoute uses it:** `app/routing/candidate_routes.py` calls
`networkx.shortest_simple_paths` (networkx's implementation of Yen's
algorithm) after flattening the MultiDiGraph to a simple DiGraph with
precomputed edge weights (Yen's networkx implementation doesn't support
multigraphs). The first returned path is always identical to Dijkstra's
optimal path (verified in `test_candidate_routes.py::
test_first_candidate_matches_dijkstra`), and subsequent paths are the
next-cheapest *distinct* routes.

**Why this instead of random perturbation:** perturbing edge weights
randomly to get "different" paths does not guarantee the resulting
paths are actually good, or that duplicate paths aren't produced. Yen's
algorithm guarantees both distinctness and a meaningful cost ordering,
which is what makes the downstream QUBO selection problem meaningful
("route #2 really is the second-best option," not an arbitrary
alternative).

**Complexity:** O(k · V · (E + V log V)) in the general case. For our
demo graph and k ≤ 8 this is a few milliseconds; see
`docs/limitations.md` for the city-scale caveat.
