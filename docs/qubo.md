# QUBO Formulation

## Why a candidate-route formulation, not a full edge-selection QUBO

A "one binary variable per road segment" QUBO for a full city graph
would need tens of thousands of variables and a Q matrix with 10^8+
entries — infeasible to build or meaningfully solve on a laptop, and
dishonest to present as "solved" without dedicated annealing hardware.
Instead, following the problem statement's own suggestion, we:

1. Generate k good, distinct candidate routes classically (Yen's
   algorithm — see `docs/algorithms.md`).
2. Use QUBO + quantum-inspired optimization to select the best **one**
   among them.

This keeps the QUBO small (k variables) while remaining a genuine
binary quadratic optimization problem — not a toy, not a random matrix
relabeled as "QUBO."

## Binary variables

```
x_i ∈ {0, 1}   for i = 1..k
x_i = 1  ⟺  candidate route i is selected
```

## Objective function

```
H_cost(x) = Σ_i  c_i · x_i
```
where `c_i` is route *i*'s total normalized multi-objective cost (see
`docs/optimization.md` for the cost function itself). Lower is better.

## Constraint

Exactly one route must be selected:
```
Σ_i x_i = 1
```

## Penalty term (turning the constraint into part of the QUBO)

```
H_penalty(x) = P · (Σ_i x_i − 1)²
             = P · ( Σ_i x_i² + 2·Σ_{i<j} x_i·x_j − 2·Σ_i x_i + 1 )
```
Since `x_i` is binary, `x_i² = x_i`, so this expands into linear
diagonal terms and quadratic off-diagonal terms — exactly the shape of
a QUBO.

## Full QUBO objective (minimize)

```
H(x) = H_cost(x) + H_penalty(x) = xᵀQx   (constant term dropped)
```

## Q matrix construction

```
Q[i][i] = c_i − P          (diagonal / linear term)
Q[i][j] = 2·P   for i ≠ j  (off-diagonal / coupling term)
```
Implemented exactly this way in `app/optimization/qubo.py::
build_route_selection_qubo` — no approximation, no randomization.

## Penalty weight P

```
P = penalty_multiplier · max(c_i)     (default penalty_multiplier = 3.0)
```

**Why this choice works:** the *worst-case* extra energy from violating
the constraint by one unit (selecting one extra route, or zero routes)
is proportional to `P`, while the *maximum possible* benefit from
picking a cheaper route instead of a more expensive one is bounded by
`max(c_i) − min(c_i) ≤ max(c_i)`. Setting `P = 3 · max(c_i)` guarantees
the penalty for any constraint violation exceeds any possible cost
saving, so the true optimum of the unconstrained QUBO always satisfies
the constraint. This is empirically confirmed in
`tests/unit/test_qubo.py::test_penalty_prevents_selecting_two_routes`
and `test_penalty_prevents_selecting_zero_routes`.

## Energy / objective value

For any candidate solution vector `x`, its QUBO energy is computed
exactly as `xᵀQx` (`QUBOProblem.energy()`) — no approximation. This is
literally what the annealer (see `docs/optimization.md`) is minimizing,
and what's reported as `solver_best_energy` in the API response.

## Verifying correctness against brute force

Because our QUBOs are small (k ≤ ~8 in practice), we can exhaustively
enumerate all `2^k` binary vectors and find the true global optimum
(`app/optimization/qubo.py::brute_force_optimum`). This is used purely
for testing — `tests/unit/test_optimizer.py` checks that simulated
annealing matches this true optimum in the large majority of
independent runs, which is the actual, checkable correctness claim we
make (see `docs/optimization.md` for the honest statistics).
