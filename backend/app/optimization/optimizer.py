"""
QuantumRoute optimization pipeline.

Ties together:
  1. Candidate route generation
  2. QUBO formulation over those candidates
  3. Quantum-inspired simulated annealing

The result includes transparency information allowing the SA solution
to be compared against the exact optimum for small candidate sets.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import List, Optional

import networkx as nx
import numpy as np

from app.optimization.qubo import (
    QUBOProblem,
    build_route_selection_qubo,
    brute_force_optimum,
)
from app.optimization.simulated_annealing import (
    AnnealingResult,
    repair_to_valid_selection,
    simulated_annealing,
)
from app.routing.baseline import RouteResult
from app.routing.candidate_routes import CandidateSet, generate_candidate_routes
from app.routing.cost import CostWeights
from app.simulation.traffic import TrafficSnapshot


@dataclass
class OptimizationResult:
    selected_route: Optional[RouteResult]
    candidate_routes: List[RouteResult]
    selected_index: Optional[int]

    qubo_size: int
    qubo_penalty: float
    solver: AnnealingResult

    was_repaired: bool
    feasible_selection: bool

    exact_optimal_index: Optional[int]
    exact_optimal_cost: Optional[float]
    selected_cost: Optional[float]
    optimality_gap_pct: Optional[float]
    matches_exact_optimum: Optional[bool]

    candidate_generation_time_ms: float
    qubo_build_time_ms: float
    total_pipeline_time_ms: float

    found: bool
    reason: Optional[str] = None


def _verify_against_exact_optimum(
    problem: QUBOProblem,
    costs: List[float],
    selected_index: int,
) -> tuple[
    Optional[int],
    Optional[float],
    Optional[float],
    Optional[bool],
]:
    """
    Verify the selected route against the exact QUBO optimum.

    Exact enumeration is intentionally limited to small candidate sets.
    For larger QUBOs, returning None is preferable to hiding an expensive
    exponential computation behind the API.
    """
    if problem.num_variables > 20:
        return None, None, costs[selected_index], None

    exact_x, _exact_energy = brute_force_optimum(problem)

    exact_indices = np.flatnonzero(exact_x)

    if len(exact_indices) != 1:
        return None, None, costs[selected_index], None

    exact_index = int(exact_indices[0])
    exact_cost = float(costs[exact_index])
    selected_cost = float(costs[selected_index])

    if exact_cost == 0:
        gap_pct = 0.0 if selected_cost == 0 else None
    else:
        gap_pct = max(
            0.0,
            (selected_cost - exact_cost) / abs(exact_cost) * 100.0,
        )

    return (
        exact_index,
        exact_cost,
        selected_cost,
        exact_index == selected_index,
    )


def run_optimization(
    G: nx.MultiDiGraph,
    source: int,
    target: int,
    traffic: Optional[TrafficSnapshot] = None,
    weights: Optional[CostWeights] = None,
    k_candidates: int = 5,
    iterations: int = 2000,
    seed: int = 42,
) -> OptimizationResult:
    weights = weights or CostWeights()
    pipeline_start = time.perf_counter()

    candidate_set: CandidateSet = generate_candidate_routes(
        G,
        source,
        target,
        traffic,
        weights,
        k=k_candidates,
    )

    if candidate_set.returned_k == 0:
        elapsed = (time.perf_counter() - pipeline_start) * 1000

        return OptimizationResult(
            selected_route=None,
            candidate_routes=[],
            selected_index=None,
            qubo_size=0,
            qubo_penalty=0.0,
            solver=AnnealingResult(
                best_x=np.array([]),
                best_energy=0.0,
                iterations=0,
                runtime_ms=0.0,
            ),
            was_repaired=False,
            feasible_selection=False,
            exact_optimal_index=None,
            exact_optimal_cost=None,
            selected_cost=None,
            optimality_gap_pct=None,
            matches_exact_optimum=None,
            candidate_generation_time_ms=candidate_set.generation_time_ms,
            qubo_build_time_ms=0.0,
            total_pipeline_time_ms=round(elapsed, 3),
            found=False,
            reason=(
                "No candidate routes could be generated "
                "(source/target likely disconnected under current "
                "traffic conditions, e.g. a closure cutting off "
                "the only path)."
            ),
        )

    costs = [float(r.total_cost) for r in candidate_set.routes]

    qubo_start = time.perf_counter()
    problem: QUBOProblem = build_route_selection_qubo(costs)
    qubo_build_ms = (time.perf_counter() - qubo_start) * 1000

    solver_result = simulated_annealing(
        problem,
        iterations=iterations,
        seed=seed,
    )

    raw_feasible = problem.is_valid_selection(solver_result.best_x)

    was_repaired = not raw_feasible

    final_x = (
        repair_to_valid_selection(problem, solver_result.best_x)
        if was_repaired
        else solver_result.best_x
    )

    feasible_selection = problem.is_valid_selection(final_x)

    if not feasible_selection:
        elapsed = (time.perf_counter() - pipeline_start) * 1000

        return OptimizationResult(
            selected_route=None,
            candidate_routes=candidate_set.routes,
            selected_index=None,
            qubo_size=problem.num_variables,
            qubo_penalty=problem.penalty,
            solver=solver_result,
            was_repaired=was_repaired,
            feasible_selection=False,
            exact_optimal_index=None,
            exact_optimal_cost=None,
            selected_cost=None,
            optimality_gap_pct=None,
            matches_exact_optimum=None,
            candidate_generation_time_ms=candidate_set.generation_time_ms,
            qubo_build_time_ms=round(qubo_build_ms, 3),
            total_pipeline_time_ms=round(elapsed, 3),
            found=False,
            reason="Simulated annealing produced an invalid route selection.",
        )

    selected_index = int(np.argmax(final_x))
    selected_route = candidate_set.routes[selected_index]

    (
        exact_optimal_index,
        exact_optimal_cost,
        selected_cost,
        matches_exact_optimum,
    ) = _verify_against_exact_optimum(
        problem,
        costs,
        selected_index,
    )

    optimality_gap_pct = None

    if (
        exact_optimal_cost is not None
        and selected_cost is not None
        and exact_optimal_cost != 0
    ):
        optimality_gap_pct = max(
            0.0,
            (selected_cost - exact_optimal_cost)
            / abs(exact_optimal_cost)
            * 100.0,
        )
    elif (
        exact_optimal_cost is not None
        and selected_cost is not None
        and exact_optimal_cost == 0
    ):
        optimality_gap_pct = (
            0.0 if selected_cost == 0 else None
        )

    total_elapsed = (time.perf_counter() - pipeline_start) * 1000

    return OptimizationResult(
        selected_route=selected_route,
        candidate_routes=candidate_set.routes,
        selected_index=selected_index,
        qubo_size=problem.num_variables,
        qubo_penalty=problem.penalty,
        solver=solver_result,
        was_repaired=was_repaired,
        feasible_selection=feasible_selection,
        exact_optimal_index=exact_optimal_index,
        exact_optimal_cost=exact_optimal_cost,
        selected_cost=selected_cost,
        optimality_gap_pct=optimality_gap_pct,
        matches_exact_optimum=matches_exact_optimum,
        candidate_generation_time_ms=candidate_set.generation_time_ms,
        qubo_build_time_ms=round(qubo_build_ms, 3),
        total_pipeline_time_ms=round(total_elapsed, 3),
        found=True,
    )
