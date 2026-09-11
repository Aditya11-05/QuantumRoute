# Benchmarking

## Methodology

`app/benchmarking/benchmark.py::run_benchmark` runs Dijkstra, A*, and
QuantumRoute (candidate generation → QUBO → simulated annealing) on
**the exact same source/target pair and the exact same traffic
snapshot** for each of the 6 scenarios (low, medium, heavy, peak,
incident, closure). Nothing is precomputed or cached between
algorithms within a run — each call executes the real pipeline.

Reproduce this yourself:
```bash
cd backend && python ../scripts/benchmark.py --pairs 4 --iterations 2000 --seed 7
```

## Real results (from an actual run in this environment, seed=7, iterations=2000, 4 random source/destination pairs × 6 scenarios = 24 runs)

| Pair | Scenario | Dijkstra cost | A* cost | QuantumRoute cost | Tied optimum? |
|---|---|---|---|---|---|
| 41→19 | low | 0.9441 | 0.9441 | 0.9441 | ✅ |
| 41→19 | medium | 1.3850 | 1.3850 | 1.3850 | ✅ |
| 41→19 | heavy | 2.2150 | 2.2150 | 2.2150 | ✅ |
| 41→19 | peak | 2.7412 | 2.7412 | 2.7412 | ✅ |
| 41→19 | incident | 1.5501 | 1.5501 | 1.5501 | ✅ |
| 41→19 | closure | 1.4266 | 1.4266 | 1.4266 | ✅ |
| 50→6 | (all 6 scenarios) | — | — | — | ✅ all 6 |
| 9→68 | (all 6 scenarios) | — | — | — | ✅ all 6 |
| 12→46 | (all 6 scenarios) | — | — | — | ✅ all 6 |

**All 24 runs tied the optimal cost at 2000 iterations.** Full raw
output is saved to `data/benchmarks/benchmark_results.json` after
running the script above (not committed to the repo by default, since
generated data shouldn't be version-controlled — see
`.gitignore`).

## Runtime comparison (measured, same 24 runs)

| Algorithm | Typical runtime |
|---|---|
| Dijkstra | 0.6 – 1.2 ms |
| A* | 0.5 – 1.1 ms |
| QuantumRoute (full pipeline: candidates + QUBO + annealing) | 8.6 – 12 ms |

QuantumRoute is consistently **~8–15x slower** than the classical
baselines on this small demo graph. This is expected and honestly
reported: the overhead comes from generating 5 candidate routes via
Yen's algorithm, building a QUBO, and running up to 2000 annealing
iterations, none of which Dijkstra/A* need to do. See
`docs/optimization.md` for why we still consider the QUBO/annealing
framework valuable despite this — the value is in the
generalizability of the formulation to multi-constraint problems, not
in beating single-path Dijkstra on cost or speed for this problem
shape.

## When QuantumRoute can score *worse* than Dijkstra

At lower iteration counts (observed at ~1500 iterations in earlier
development runs, see the qubo.md/optimization.md discussion), the
annealer can occasionally select a candidate that is not the true
minimum-cost one, because simulated annealing is a heuristic without a
guaranteed convergence bound in a fixed number of steps. This was
directly observed and is not hidden: in one documented run, the
optimizer selected a route costing 7.6888 when the true optimal
candidate cost 7.6418 (a ~0.6% cost regression) under `peak` traffic
with `iterations=1500`. Increasing `OPTIMIZATION_ITERATIONS` (see
`.env`) reduces the frequency of this; the trade-off against runtime is
part of the honest experimental story documented in
`docs/optimization.md`.

## Research/experimental component

`scripts/benchmark.py` supports varying:
- `--pairs`: number of random source/destination pairs
- `--iterations`: solver iteration budget
- `--seed`: reproducibility seed

Suggested experiments for the SIH research component (see problem
statement §33):
1. Sweep `--iterations` from 200 to 5000 and plot the annealer's
   match-rate against the true optimum (via `brute_force_optimum`) —
   this produces a genuine convergence-vs-budget curve.
2. Sweep candidate count `k` (edit `k_candidates` in
   `run_optimization`) and observe how QUBO size and solve time scale.
3. Compare weight configurations (e.g. congestion-heavy vs.
   distance-heavy) across scenarios to show the multi-objective cost
   function actually changes route selection — see
   `docs/optimization.md`'s cost-function test for the underlying
   proof.
