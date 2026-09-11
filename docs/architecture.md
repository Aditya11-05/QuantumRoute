# QuantumRoute — Architecture

## System overview

```
React Dashboard (Vite + TS + Leaflet)
        │  HTTP/JSON
        ▼
FastAPI Backend
        │
        ├── Road network (OSMnx/NetworkX graph, cached or synthetic)
        ├── Traffic simulator (synthetic, seeded, scenario-based)
        ├── ML congestion predictor (LightGBM, trained on synthetic data)
        ├── Multi-objective cost function (travel time, congestion,
        │    distance, fuel proxy, intersections, incidents)
        ├── Baseline routing (Dijkstra, A*)
        ├── Candidate route generation (Yen's k-shortest-paths)
        ├── QUBO formulation (route selection, exactly-one constraint)
        ├── Quantum-inspired solver (simulated annealing, classical hardware)
        └── Benchmarking (runs all three algorithms on identical inputs)
```

## Why this shape

The problem statement asks for a system that chooses routes using more
than raw shortest-distance, and asks specifically for a QUBO / quantum-
inspired component. The natural, honest way to combine those
requirements without either (a) ignoring the quantum requirement or
(b) building a fictional "real quantum" system is:

1. Use the graph + traffic + ML + cost function to produce a *set* of
   good candidate routes (this is where "smarter than shortest-path"
   actually happens - the cost function incorporates six weighted
   objectives, not just distance).
2. Use a genuine, from-scratch QUBO to frame "which of these candidates
   is best" as a quadratic binary optimization problem.
3. Solve that QUBO with simulated annealing - a classical algorithm
   that is explicitly, honestly "quantum-inspired" (same energy-
   minimization idea as quantum annealing hardware, zero quantum
   hardware involved).

This keeps every stage individually small, testable, and defensible,
rather than one monolithic "black box that outputs a route".

## Backend module map

| Module | Responsibility |
|---|---|
| `app/routing/graph_loader.py` | Load real OSM graph (live) or deterministic synthetic graph (demo/offline) |
| `app/routing/node_utils.py` | Nearest-node lookup, haversine distance |
| `app/routing/cost.py` | Multi-objective edge cost function |
| `app/routing/baseline.py` | Dijkstra, A* |
| `app/routing/candidate_routes.py` | Yen's k-shortest-paths candidate generation |
| `app/simulation/traffic.py` | Synthetic traffic scenario simulator |
| `app/ml/*` | Feature engineering, synthetic dataset, LightGBM training, inference |
| `app/optimization/qubo.py` | QUBO construction for route selection |
| `app/optimization/simulated_annealing.py` | Quantum-inspired classical solver |
| `app/optimization/optimizer.py` | Wires candidates → QUBO → solver → selected route |
| `app/benchmarking/benchmark.py` | Runs Dijkstra/A*/QuantumRoute head-to-head |
| `app/api/*` | FastAPI routers |
| `app/state.py` | Process-wide graph/model singletons |

## Frontend module map

| Path | Responsibility |
|---|---|
| `src/pages/Dashboard.tsx` | Main page, layout, state orchestration |
| `src/map/RouteMap.tsx` | Leaflet map: click-to-pin, route polylines |
| `src/components/*` | Weight sliders, comparison table, optimization details, AI prediction panel |
| `src/charts/ConvergenceChart.tsx` | Recharts line chart of solver convergence |
| `src/services/api.ts` | Typed fetch wrapper for the backend API |
| `src/types/api.ts` | TypeScript types mirroring backend Pydantic schemas |

## Directed graph note

Real road networks contain one-way streets, so the graph is a
`networkx.MultiDiGraph` (directed, multi-edge) throughout - a directed
edge (u → v) does not imply an edge (v → u) exists. The synthetic demo
graph deliberately marks ~12% of segments one-way to exercise this
correctly (see `graph_loader.py::_build_synthetic_graph`), and several
tests assert weak-connectivity (reachability ignoring direction) rather
than strong connectivity, since strongly-connected is not guaranteed
(and isn't true of real cities either).
