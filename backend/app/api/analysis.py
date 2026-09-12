from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.config.settings import get_settings
from app.api.routing import (
    _build_traffic_snapshot,
    _route_result_to_response,
    _weights_from_request,
)
from app.routing.baseline import astar_route, dijkstra_route
from app.routing.node_utils import nearest_node
from app.optimization.optimizer import run_optimization
from app.schemas.routing import RouteRequest
from app.state import get_graph_state

router = APIRouter(tags=["analysis"])


def _pct_change(new_value: float, old_value: float):
    if old_value == 0:
        return None
    return (new_value - old_value) / abs(old_value) * 100.0


@router.post("/route/analysis")
def route_analysis(req: RouteRequest):
    """
    Full research analysis pipeline.

    Uses the same real traffic snapshot for:
      - Dijkstra baseline
      - A* baseline
      - candidate route generation
      - QUBO construction
      - simulated annealing

    In research mode, _build_traffic_snapshot() fails closed unless
    the real METR-LA artifacts are available and the timestamp is valid.
    """
    lg = get_graph_state()
    G = lg.graph
    settings = get_settings()

    weights = _weights_from_request(req.weights)

    # ---------------------------------------------------------
    # SNAP REQUEST COORDINATES TO THE REAL OSM GRAPH
    # ---------------------------------------------------------
    try:
        src_node, src_dist = nearest_node(
            G,
            req.source.lat,
            req.source.lon,
        )

        dst_node, dst_dist = nearest_node(
            G,
            req.destination.lat,
            req.destination.lon,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc

    # ---------------------------------------------------------
    # ONE SHARED TRAFFIC SNAPSHOT
    # ---------------------------------------------------------
    snapshot, traffic_meta = _build_traffic_snapshot(req)

    # ---------------------------------------------------------
    # CLASSICAL BASELINES
    # ---------------------------------------------------------
    dijkstra = dijkstra_route(
        G,
        src_node,
        dst_node,
        snapshot,
        weights,
    )

    astar = astar_route(
        G,
        src_node,
        dst_node,
        snapshot,
        weights,
    )

    # ---------------------------------------------------------
    # QUANTUM-INSPIRED OPTIMIZATION
    # ---------------------------------------------------------
    optimization = run_optimization(
        G,
        src_node,
        dst_node,
        snapshot,
        weights,
        k_candidates=5,
        iterations=settings.OPTIMIZATION_ITERATIONS,
    )

    dijkstra_response = _route_result_to_response(
        dijkstra,
        lg.source,
        lg.region,
    )

    astar_response = _route_result_to_response(
        astar,
        lg.source,
        lg.region,
    )

    candidate_responses = [
        _route_result_to_response(
            route,
            lg.source,
            lg.region,
        )
        for route in optimization.candidate_routes
    ]

    selected_response = None

    if optimization.selected_route is not None:
        selected_response = _route_result_to_response(
            optimization.selected_route,
            lg.source,
            lg.region,
        )

    # ---------------------------------------------------------
    # COMPARISON
    # ---------------------------------------------------------
    baseline_distance = float(dijkstra.total_distance_m)
    baseline_time = float(dijkstra.total_travel_time_sec)
    baseline_cost = float(dijkstra.total_cost)

    optimized_distance = (
        float(optimization.selected_route.total_distance_m)
        if optimization.selected_route is not None
        else baseline_distance
    )

    optimized_time = (
        float(optimization.selected_route.total_travel_time_sec)
        if optimization.selected_route is not None
        else baseline_time
    )

    optimized_cost = (
        float(optimization.selected_route.total_cost)
        if optimization.selected_route is not None
        else baseline_cost
    )

    distance_delta = optimized_distance - baseline_distance
    time_delta = optimized_time - baseline_time
    cost_delta = optimized_cost - baseline_cost

    # ---------------------------------------------------------
    # INTERPRETATION / PROVENANCE
    # ---------------------------------------------------------
    interpretation = {
        "baseline": (
            "Dijkstra is the classical shortest-path baseline "
            "using the same graph, traffic snapshot, and objective weights."
        ),
        "astar": (
            "A* is a second classical baseline using the same "
            "traffic-aware edge costs."
        ),
        "optimizer": (
            "QuantumRoute generates candidate routes, formulates "
            "route selection as a QUBO, and solves it with classical "
            "simulated annealing."
        ),
        "comparison": (
            "Reported changes are computed directly from the returned "
            "Dijkstra and selected QuantumRoute route costs."
        ),
        "optimality": (
            "For small candidate sets, the selected solution is checked "
            "against exact QUBO enumeration."
        ),
    }

    return {
        "found": bool(
            dijkstra.found
            and optimization.found
            and selected_response is not None
        ),
        "reason": optimization.reason,
        "baseline": {
            "dijkstra": dijkstra_response if dijkstra.found else None,
            "astar": astar_response if astar.found else None,
        },
        "optimization": {
            "selected_route": selected_response,
            "candidate_routes": candidate_responses,
            "selected_index": optimization.selected_index,
            "qubo_size": optimization.qubo_size,
            "qubo_penalty": optimization.qubo_penalty,
            "solver_iterations": optimization.solver.iterations,
            "solver_runtime_ms": optimization.solver.runtime_ms,
            "solver_best_energy": optimization.solver.best_energy,
            "solver_convergence_history": (
                optimization.solver.convergence_history
            ),
            "was_repaired": optimization.was_repaired,
            "feasible_selection": optimization.feasible_selection,
            "candidate_generation_time_ms": (
                optimization.candidate_generation_time_ms
            ),
            "qubo_build_time_ms": optimization.qubo_build_time_ms,
            "total_pipeline_time_ms": optimization.total_pipeline_time_ms,
            "exact_optimal_index": optimization.exact_optimal_index,
            "exact_optimal_cost": optimization.exact_optimal_cost,
            "selected_cost": optimization.selected_cost,
            "optimality_gap_pct": optimization.optimality_gap_pct,
            "matches_exact_optimum": optimization.matches_exact_optimum,
        },
        "comparison": {
            "distance_delta_m": distance_delta,
            "travel_time_delta_sec": time_delta,
            "cost_delta": cost_delta,
            "distance_change_pct": _pct_change(
                optimized_distance,
                baseline_distance,
            ),
            "travel_time_change_pct": _pct_change(
                optimized_time,
                baseline_time,
            ),
            "cost_change_pct": _pct_change(
                optimized_cost,
                baseline_cost,
            ),
        },
        "snap": {
            "source_distance_m": round(src_dist, 1),
            "destination_distance_m": round(dst_dist, 1),
        },
        "traffic": {
            "mode": traffic_meta["mode"],
            "traffic_provenance": traffic_meta["traffic_provenance"],
            "traffic_scenario": traffic_meta["traffic_scenario"],
            "timestamp": traffic_meta.get("timestamp"),
        },
        "network": {
            "graph_source": lg.source,
            "region": lg.region,
            "num_nodes": G.number_of_nodes(),
            "num_edges": G.number_of_edges(),
        },
        "weights": {
            "travel_time": weights.travel_time,
            "congestion": weights.congestion,
            "distance": weights.distance,
            "fuel": weights.fuel,
            "intersection": weights.intersection,
            "incident": weights.incident,
        },
        "interpretation": interpretation,
        "quantum_disclaimer": (
            "This optimization is QUANTUM-INSPIRED (simulated annealing) "
            "and runs entirely on classical CPU hardware. No quantum "
            "computer or quantum circuit is used."
        ),
    }
