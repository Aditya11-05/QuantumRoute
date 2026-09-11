"""
Benchmarking: actually run Dijkstra, A*, and QuantumRoute (QUBO +
simulated annealing over candidate routes) on the SAME source/target
under each traffic scenario, and report the real resulting numbers.

We do not guarantee QuantumRoute wins - see run_optimization/optimizer.py
docstring: since Dijkstra's own optimal path is always included among
the candidate routes QuantumRoute selects from, QuantumRoute can at
best tie Dijkstra's cost, and can score slightly worse if the
metaheuristic doesn't converge to the true optimum in the configured
iteration budget. This module reports whatever actually happens.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import networkx as nx

from app.optimization.optimizer import run_optimization
from app.routing.baseline import astar_route, dijkstra_route
from app.routing.cost import CostWeights
from app.simulation.traffic import TrafficScenario, simulate_traffic


@dataclass
class AlgoRunResult:
    algorithm: str
    found: bool
    distance_m: float
    travel_time_sec: float
    total_cost: float
    runtime_ms: float


@dataclass
class ScenarioResult:
    scenario: str
    results: List[AlgoRunResult]


def run_benchmark(
    G: nx.MultiDiGraph,
    source: int,
    target: int,
    scenarios: Optional[List[str]] = None,
    weights: Optional[CostWeights] = None,
    seed: int = 42,
    k_candidates: int = 5,
    iterations: int = 2000,
) -> List[ScenarioResult]:
    weights = weights or CostWeights()
    scenario_names = scenarios or [s.value for s in TrafficScenario]

    all_results: List[ScenarioResult] = []
    for name in scenario_names:
        scenario = TrafficScenario(name.lower())
        snapshot = simulate_traffic(G, scenario, seed=seed)

        d = dijkstra_route(G, source, target, snapshot, weights)
        a = astar_route(G, source, target, snapshot, weights)
        opt = run_optimization(G, source, target, snapshot, weights, k_candidates=k_candidates, iterations=iterations, seed=seed)

        results = [
            AlgoRunResult("dijkstra", d.found, d.total_distance_m, d.total_travel_time_sec, d.total_cost, d.computation_time_ms),
            AlgoRunResult("astar", a.found, a.total_distance_m, a.total_travel_time_sec, a.total_cost, a.computation_time_ms),
        ]
        if opt.found:
            results.append(AlgoRunResult(
                "quantumroute", True, opt.selected_route.total_distance_m,
                opt.selected_route.total_travel_time_sec, opt.selected_route.total_cost,
                opt.total_pipeline_time_ms,
            ))
        else:
            results.append(AlgoRunResult("quantumroute", False, 0.0, 0.0, 0.0, opt.total_pipeline_time_ms))

        all_results.append(ScenarioResult(scenario=name, results=results))

    return all_results
