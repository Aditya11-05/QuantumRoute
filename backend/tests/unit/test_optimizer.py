from __future__ import annotations

import numpy as np

from app.optimization.qubo import build_route_selection_qubo, brute_force_optimum
from app.optimization.simulated_annealing import simulated_annealing, repair_to_valid_selection


def test_annealing_matches_brute_force_most_of_the_time():
    """
    Honest correctness check: simulated annealing is a heuristic, not
    guaranteed optimal on every run. We assert it matches the true
    (brute-force) optimum in the large majority of independent seeded
    runs, which is the real, checkable claim - not "always wins".
    """
    costs = [6.1538, 6.1667, 6.1698, 6.1847, 6.1926]
    problem = build_route_selection_qubo(costs)
    true_best_x, _ = brute_force_optimum(problem)
    true_best_idx = int(np.argmax(true_best_x))

    matches = 0
    n_trials = 15
    for seed in range(n_trials):
        result = simulated_annealing(problem, iterations=2000, seed=seed)
        x = repair_to_valid_selection(problem, result.best_x)
        if int(np.argmax(x)) == true_best_idx:
            matches += 1

    assert matches / n_trials >= 0.6, f"SA only matched brute force optimum {matches}/{n_trials} times"


def test_annealing_convergence_history_is_non_increasing():
    """convergence_history tracks *best-so-far* energy, so it must never increase."""
    problem = build_route_selection_qubo([3.0, 1.0, 2.0])
    result = simulated_annealing(problem, iterations=500, seed=1)
    history = result.convergence_history
    for i in range(1, len(history)):
        assert history[i] <= history[i - 1] + 1e-9


def test_repair_fixes_invalid_all_zero_selection():
    problem = build_route_selection_qubo([3.0, 1.0, 2.0])
    invalid = np.array([0.0, 0.0, 0.0])
    fixed = repair_to_valid_selection(problem, invalid)
    assert problem.is_valid_selection(fixed)
    assert int(np.argmax(fixed)) == 1  # cheapest route


def test_repair_fixes_invalid_multi_selection():
    problem = build_route_selection_qubo([3.0, 1.0, 2.0])
    invalid = np.array([1.0, 1.0, 1.0])
    fixed = repair_to_valid_selection(problem, invalid)
    assert problem.is_valid_selection(fixed)
    assert int(np.argmax(fixed)) == 1


def test_repair_leaves_valid_selection_untouched():
    problem = build_route_selection_qubo([3.0, 1.0, 2.0])
    valid = np.array([0.0, 1.0, 0.0])
    fixed = repair_to_valid_selection(problem, valid)
    assert np.array_equal(fixed, valid)


def test_annealing_runtime_recorded():
    problem = build_route_selection_qubo([1.0, 2.0])
    result = simulated_annealing(problem, iterations=100, seed=1)
    assert result.runtime_ms >= 0
    assert result.iterations == 100
    assert result.accepted_moves + result.rejected_moves == 100
