"""
Constraint-aware simulated annealing QUBO solver.

This is a classical simulated-annealing implementation. It is
"quantum-inspired" only in the sense that it uses an annealing-based
energy-minimization strategy; it does not execute quantum computation.

For the route-selection QUBO, the constraint is:

    sum(x_i) = 1

Therefore the production neighborhood preserves this constraint directly:
one selected route is replaced by another selected route.

This avoids spending most of the search in infeasible multi-route states
and makes the annealing process appropriate for the actual optimization
problem.
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from typing import List

import numpy as np

from app.optimization.qubo import QUBOProblem


@dataclass
class AnnealingResult:
    best_x: np.ndarray
    best_energy: float
    iterations: int
    runtime_ms: float
    convergence_history: List[float] = field(default_factory=list)
    accepted_moves: int = 0
    rejected_moves: int = 0
    final_temperature: float = 0.0
    initial_temperature: float = 0.0
    cooling_rate: float = 0.0
    seed: int = 0


def simulated_annealing(
    problem: QUBOProblem,
    iterations: int = 2000,
    initial_temperature: float = 10.0,
    cooling_rate: float = 0.995,
    seed: int = 42,
) -> AnnealingResult:
    """
    Run constraint-aware simulated annealing on a route-selection QUBO.

    The route-selection formulation requires exactly one selected route.
    Consequently, the neighborhood swaps the currently selected route
    with another route instead of independently flipping arbitrary bits.

    Every visited state is therefore a valid one-hot route selection.
    """

    if problem.num_variables < 1:
        raise ValueError("QUBO must contain at least one variable.")

    if iterations < 0:
        raise ValueError("iterations must be non-negative.")

    if initial_temperature <= 0:
        raise ValueError("initial_temperature must be positive.")

    if not 0 < cooling_rate <= 1:
        raise ValueError("cooling_rate must be in (0, 1].")

    rng = random.Random(seed)
    k = problem.num_variables

    # Start from exactly one selected route.
    current_idx = rng.randrange(k)

    x = np.zeros(k, dtype=float)
    x[current_idx] = 1.0

    current_energy = problem.energy(x)

    best_x = x.copy()
    best_energy = current_energy

    history: List[float] = [best_energy]

    accepted = 0
    rejected = 0

    temperature = initial_temperature

    start = time.perf_counter()

    for _ in range(iterations):
        # With one variable there is no alternative route to propose.
        if k > 1:
            candidate_idx = rng.randrange(k - 1)

            # Map [0, k-2] onto all indices except current_idx.
            if candidate_idx >= current_idx:
                candidate_idx += 1

            candidate_x = np.zeros(k, dtype=float)
            candidate_x[candidate_idx] = 1.0

            candidate_energy = problem.energy(candidate_x)
            delta = candidate_energy - current_energy

            if delta <= 0:
                accept = True
            else:
                probability = math.exp(
                    -delta / max(temperature, 1e-12)
                )
                accept = rng.random() < probability

            if accept:
                current_idx = candidate_idx
                x = candidate_x
                current_energy = candidate_energy
                accepted += 1
            else:
                rejected += 1

        history.append(best_energy)

        if current_energy < best_energy:
            best_energy = current_energy
            best_x = x.copy()
            history[-1] = best_energy
        else:
            # Explicitly retain best-so-far semantics.
            history[-1] = best_energy

        temperature *= cooling_rate

    elapsed_ms = (time.perf_counter() - start) * 1000

    return AnnealingResult(
        best_x=best_x,
        best_energy=best_energy,
        iterations=iterations,
        runtime_ms=round(elapsed_ms, 3),
        convergence_history=history,
        accepted_moves=accepted,
        rejected_moves=rejected,
        final_temperature=temperature,
        initial_temperature=initial_temperature,
        cooling_rate=cooling_rate,
        seed=seed,
    )


def repair_to_valid_selection(
    problem: QUBOProblem,
    x: np.ndarray,
) -> np.ndarray:
    """
    Safety guard for callers that provide an arbitrary binary state.

    Production simulated annealing already produces valid one-hot states.
    This function remains available as a defensive boundary for external
    callers and tests.
    """

    x = np.asarray(x, dtype=float)
    selected = [i for i, value in enumerate(x) if value > 0.5]

    if len(selected) == 1:
        return x

    fixed = np.zeros_like(x)

    if len(selected) == 0:
        best_i = int(np.argmin(problem.route_costs))
    else:
        best_i = min(
            selected,
            key=lambda i: problem.route_costs[i],
        )

    fixed[best_i] = 1.0
    return fixed
