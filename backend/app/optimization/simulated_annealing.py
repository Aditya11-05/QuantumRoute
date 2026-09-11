"""
Simulated Annealing QUBO solver.

HONESTY NOTE (read this before claiming anything about "quantum" in a
demo or report):
This solver is a classical metaheuristic. It is called "quantum-
inspired" because its acceptance rule (occasionally accepting a worse
solution based on a temperature-controlled probability) is the same
mechanism used in quantum annealing hardware (e.g. D-Wave) to escape
local minima via thermal (here, simulated) rather than quantum
fluctuations. IT RUNS ENTIRELY ON CLASSICAL CPU HARDWARE. No qubits,
no quantum circuit, no quantum speedup is claimed or measured anywhere
in this codebase. If a judge asks "are you using a quantum computer?"
the correct answer is: "No - we use simulated annealing, a classical
algorithm that mimics the same annealing/energy-minimization idea that
quantum annealers use, so it's 'quantum-inspired', not 'quantum'."

ALGORITHM
Standard Metropolis-criterion simulated annealing over binary vectors:
  1. Start from a random (or greedy) binary vector x.
  2. At each iteration, propose a neighbor x' by flipping one random bit.
  3. Compute delta_E = E(x') - E(x) using the QUBO energy (x^T Q x).
  4. If delta_E <= 0: accept (it's better or equal).
     Else: accept with probability exp(-delta_E / T) (Metropolis).
  5. Cool the temperature T geometrically: T *= cooling_rate.
  6. Track the best solution seen across all iterations.

CONVERGENCE HISTORY
We record the best-energy-so-far at every iteration, which is what the
frontend's "Optimizer Convergence" chart plots. This is the real
trajectory of the actual run, not a fabricated smooth curve.
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
    Run simulated annealing on the given QUBO problem.

    initial_temperature/cooling_rate are exposed as parameters (not
    hardcoded magic constants) because they materially affect solution
    quality - see docs/optimization.md for the sensitivity experiments
    referenced in the benchmarking module.
    """
    rng = random.Random(seed)
    k = problem.num_variables

    # Start from a uniformly random binary vector.
    x = np.array([rng.randint(0, 1) for _ in range(k)], dtype=float)
    current_energy = problem.energy(x)

    best_x = x.copy()
    best_energy = current_energy

    T = initial_temperature
    history: List[float] = [best_energy]
    accepted = 0
    rejected = 0

    start = time.perf_counter()
    for _ in range(iterations):
        flip_idx = rng.randrange(k)
        x_candidate = x.copy()
        x_candidate[flip_idx] = 1.0 - x_candidate[flip_idx]

        candidate_energy = problem.energy(x_candidate)
        delta = candidate_energy - current_energy

        accept = False
        if delta <= 0:
            accept = True
        else:
            T_safe = max(T, 1e-9)
            probability = math.exp(-delta / T_safe)
            accept = rng.random() < probability

        if accept:
            x = x_candidate
            current_energy = candidate_energy
            accepted += 1
        else:
            rejected += 1

        if current_energy < best_energy:
            best_energy = current_energy
            best_x = x.copy()

        history.append(best_energy)
        T *= cooling_rate

    elapsed_ms = (time.perf_counter() - start) * 1000

    return AnnealingResult(
        best_x=best_x,
        best_energy=best_energy,
        iterations=iterations,
        runtime_ms=round(elapsed_ms, 3),
        convergence_history=history,
        accepted_moves=accepted,
        rejected_moves=rejected,
        final_temperature=T,
        initial_temperature=initial_temperature,
        cooling_rate=cooling_rate,
        seed=seed,
    )


def repair_to_valid_selection(problem: QUBOProblem, x: np.ndarray) -> np.ndarray:
    """
    The annealer minimizes an unconstrained QUBO, so in rare cases
    (very few iterations, or a poorly tuned penalty) it can return an
    x that doesn't satisfy "exactly one route selected". Rather than
    silently return an invalid/undefined route, we deterministically
    repair: if zero routes selected, pick the globally cheapest route;
    if multiple selected, pick the cheapest among those selected. This
    repair step is logged/flagged by the caller so it's never silently
    hidden - see optimizer.py.
    """
    x = np.asarray(x, dtype=float)
    selected = [i for i, v in enumerate(x) if v > 0.5]

    if len(selected) == 1:
        return x

    fixed = np.zeros_like(x)
    if len(selected) == 0:
        best_i = int(np.argmin(problem.route_costs))
    else:
        best_i = min(selected, key=lambda i: problem.route_costs[i])
    fixed[best_i] = 1.0
    return fixed
