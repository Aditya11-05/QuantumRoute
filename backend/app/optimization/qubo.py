"""
QUBO (Quadratic Unconstrained Binary Optimization) formulation for
route selection.

------------------------------------------------------------------
WHY A CANDIDATE-ROUTE FORMULATION (not a full edge-selection QUBO)
------------------------------------------------------------------
A "turn every road segment into a QUBO variable" formulation for a
city-scale graph would need one binary variable per directed edge
(potentially tens of thousands), giving a Q matrix with 10^8+ entries -
infeasible to build or solve on a laptop, and dishonest to claim as
"solved" without dedicated quantum/annealing hardware. Instead we take
the *practical* approach explicitly suggested by the problem statement:
generate a small set of k good candidate routes classically (Yen's
algorithm, see candidate_routes.py), then use QUBO/quantum-inspired
optimization to choose the best ONE (or combination satisfying
constraints) among them. This keeps the QUBO small (k variables, a
k x k Q matrix) while still being a genuine binary quadratic
optimization problem, not a toy.

------------------------------------------------------------------
MATHEMATICAL FORMULATION
------------------------------------------------------------------
Binary variables:
    x_i in {0, 1} for i = 1..k
    x_i = 1  <=>  candidate route i is selected

Objective (route quality, linear in x since routes don't interact
in cost - but see constraint terms below for the quadratic part):
    H_cost(x) = sum_i  c_i * x_i
    where c_i = normalized total multi-objective cost of route i
    (from cost.py / candidate_routes.py), so lower is better.

Constraint - exactly one route must be selected:
    sum_i x_i = 1

This constraint is enforced by a quadratic penalty term (the standard
way to turn a linear-equality constraint into part of a QUBO):
    H_penalty(x) = P * (sum_i x_i - 1)^2
                 = P * ( sum_i x_i^2 + 2*sum_{i<j} x_i*x_j - 2*sum_i x_i + 1 )
Since x_i is binary, x_i^2 = x_i, so this expands into linear diagonal
terms and quadratic off-diagonal terms - which is exactly what goes
into the Q matrix.

Full QUBO objective to MINIMIZE:
    H(x) = H_cost(x) + H_penalty(x) = x^T Q x  (+ constant, dropped)

Q matrix construction (k x k, symmetric a we store as upper-triangular
plus diagonal, which is the standard QUBO convention):
    Q[i][i] = c_i + P * (1 - 2)      = c_i - P        (diagonal / linear term)
    Q[i][j] = 2 * P   for i != j                       (off-diagonal / coupling term)

PENALTY WEIGHT P:
P must be large enough that violating the constraint (selecting 0 or
>= 2 routes) is always worse than any achievable cost difference
between routes, but not so large that it drowns out the cost signal
in a solver that (like simulated annealing) accepts some uphill moves.
We set P = penalty_multiplier * max(c_i), which guarantees:
    cost of picking 2 routes (extra +P from penalty, roughly) always
    exceeds cost of picking the single best route, for the default
    multiplier we use (see qubo.py:DEFAULT_PENALTY_MULTIPLIER and the
    proof sketch in docs/qubo.md).

ENERGY / OBJECTIVE VALUE:
Given a candidate solution vector x, its QUBO energy is x^T Q x
(computed exactly here, no approximation) - this is what the
quantum-inspired solver (simulated_annealing.py) is minimizing.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np

DEFAULT_PENALTY_MULTIPLIER = 3.0


@dataclass
class QUBOProblem:
    Q: np.ndarray            # k x k symmetric-ish matrix (upper triangular convention)
    num_variables: int
    route_costs: List[float]
    penalty: float

    def energy(self, x: np.ndarray) -> float:
        """Compute x^T Q x exactly for a binary vector x (shape (k,))."""
        x = np.asarray(x, dtype=float)
        return float(x @ self.Q @ x)

    def is_valid_selection(self, x: np.ndarray) -> bool:
        return int(round(float(np.sum(x)))) == 1


def build_route_selection_qubo(
    route_costs: List[float],
    penalty_multiplier: float = DEFAULT_PENALTY_MULTIPLIER,
) -> QUBOProblem:
    """
    Build the Q matrix for the "select exactly one candidate route"
    QUBO described in the module docstring.

    route_costs: list of k non-negative normalized route costs, cheapest
    routes should have the smallest c_i.
    """
    if len(route_costs) == 0:
        raise ValueError("Need at least one candidate route to build a QUBO")

    k = len(route_costs)
    costs = np.array(route_costs, dtype=float)
    max_cost = float(np.max(costs)) if np.max(costs) > 0 else 1.0
    P = penalty_multiplier * max_cost

    Q = np.zeros((k, k), dtype=float)
    for i in range(k):
        # Diagonal term: linear cost term c_i, plus the penalty's linear
        # contribution from expanding P*(sum x - 1)^2 with x_i^2 = x_i:
        #   P*x_i^2 - 2*P*x_i  ->  (as diagonal, since x_i^2=x_i) : c_i - P
        Q[i, i] = costs[i] - P
        for j in range(i + 1, k):
            # Off-diagonal coupling term from 2*P*sum_{i<j} x_i*x_j
            Q[i, j] = 2.0 * P

    return QUBOProblem(Q=Q, num_variables=k, route_costs=route_costs, penalty=P)


def brute_force_optimum(problem: QUBOProblem) -> tuple:
    """
    Exhaustively evaluate all 2^k binary vectors and return the true
    global optimum (x*, energy*). Only used for k <= ~20 - this exists
    so we can VERIFY the simulated-annealing solver actually finds (or
    gets very close to) the true optimum, rather than just trusting it.
    See tests/unit/test_optimizer.py.
    """
    k = problem.num_variables
    if k > 20:
        raise ValueError("brute_force_optimum is only for small k (<=20) verification use")

    best_x = None
    best_energy = float("inf")
    for bits in range(2 ** k):
        x = np.array([(bits >> i) & 1 for i in range(k)], dtype=float)
        e = problem.energy(x)
        if e < best_energy:
            best_energy = e
            best_x = x
    return best_x, best_energy
