from __future__ import annotations

import numpy as np
import pytest

from app.optimization.qubo import build_route_selection_qubo, brute_force_optimum


def test_qubo_shape():
    costs = [1.0, 2.0, 3.0]
    problem = build_route_selection_qubo(costs)
    assert problem.Q.shape == (3, 3)
    assert problem.num_variables == 3


def test_qubo_prefers_cheapest_route_at_optimum():
    costs = [5.0, 1.0, 9.0, 3.0]
    problem = build_route_selection_qubo(costs)
    best_x, best_energy = brute_force_optimum(problem)
    assert problem.is_valid_selection(best_x)
    selected = int(np.argmax(best_x))
    assert selected == 1  # index of the cheapest cost (1.0)


def test_penalty_prevents_selecting_two_routes():
    """Selecting 2 routes should always cost more than selecting the single best one."""
    costs = [1.0, 1.01, 1.02]
    problem = build_route_selection_qubo(costs)

    single_best = np.array([1, 0, 0], dtype=float)
    two_selected = np.array([1, 1, 0], dtype=float)

    assert problem.energy(single_best) < problem.energy(two_selected)


def test_penalty_prevents_selecting_zero_routes():
    costs = [1.0, 2.0, 3.0]
    problem = build_route_selection_qubo(costs)

    none_selected = np.array([0, 0, 0], dtype=float)
    single_best = np.array([1, 0, 0], dtype=float)
    assert problem.energy(single_best) < problem.energy(none_selected)


def test_single_candidate_qubo():
    problem = build_route_selection_qubo([2.5])
    best_x, best_energy = brute_force_optimum(problem)
    assert best_x[0] == 1.0


def test_empty_costs_raises():
    with pytest.raises(ValueError):
        build_route_selection_qubo([])
